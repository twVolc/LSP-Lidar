# =========================================================================================
# Main file to control data acquisition/handling of both LSP and Lidar data simultaneously
# =========================================================================================
# Future work may incoorporate further data streams into this - e.g. GPS speed, tilt etc.
# handle_data() is the main function to run, this starts and controls acquisitions

from LSP_control import *
from server import Instruments, SocketServ, SocketLidStop
import numpy as np
import scipy.io as sci
import datetime
import os
import threading    # Consider using multiprocessing instead of threading - think it should be faster
from multiprocessing import Process, Queue
import queue
import subprocess
from subprocess import Popen
import time
import signal


class ArrayInfo:
    """Holds information on the array where data is stored directly after acquisition"""
    len_lsp = 1000                          # Number of data points in lsp scan
    speed_idx = len_lsp                     # Index to place the LSP scan speed information
    NUM_LIDAR_ACQ = 120                     # Number of lidar points stored per row of lsp data
    len_lidar = Instruments.NUM_LIDAR_PTS * NUM_LIDAR_ACQ # Number of data points in total for lidar per row of LSP data
    lid_idx_start = speed_idx + 1           # Start idx for putting lidar data in array
    len_array = len_lsp + 1 + len_lidar     # Total size of array needed to hold all data (1 is for scan speed info)
    NUM_SCANS = 1000                        # Number fo LSP scans saved to single file


def handle_data(_q=queue.Queue(), messages=None):
    """Function to do all of the data handling during acquisition for both the LSP and RPLIDAR"""
    # DIRECTORY SETUP FOR DATA STORAGE
    data_path = '.\\Data\\'
    date_dir = datetime.datetime.now().strftime('%Y-%m-%d')
    full_dir_path = data_path + date_dir + '\\'             # Directory to save data
    if not os.path.exists(full_dir_path):
        os.makedirs(full_dir_path)

    # Instantiate LSP object for communicating with LSP
    lsp_processor = ProcessLSP()  # Instantiate object to process data
    lsp_comms = SocketLSP('10.1.10.1', gui_message=messages)  # Instantiate communications object

    # Create Lidar socket object which automatically opens a socket and tries to receive data from ultra_simple.exe
    serv_Lidar = SocketServ(Instruments.SERVER_LIDAR, gui_message=messages)
    size_lid = serv_Lidar.num_pts_recv * Instruments.NUM_LIDAR_PTS      # Size of a single dataset packaged by serv_Lidar
    num_lidar_iter = ArrayInfo.NUM_LIDAR_ACQ / serv_Lidar.num_pts_recv  # Number of iterations before we fill lidar space for a single LSP scan in our numpy array

    # Create lidar socket for stopping instrument
    serv_lidar_stop = SocketLidStop(gui_message=messages)

    # Send initial Hello message and check response
    lsp_comms.init_comms()
    message = lsp_comms.recv_resp()
    message_list = message.split(' ')
    if message_list[1] != '0':
        if messages is not None:
            messages.message('Error code [%s] returned by LSP. Closing connections...' % message_list[1])
        else:
            print('Error code [%s] returned by LSP. Closing connections...' % message_list[1])
        lsp_comms.close_socket()
        serv_Lidar.close_socket()
        return

    # Request LSP binary stream
    lsp_comms.req_stream_bin()
    resp = lsp_comms.recv_stream_resp()
    if resp != 0:
        if messages is not None:
            messages.message('Error code [%i] returned by LSP. Closing connections...' % resp)
        else:
            print('Error code [%i] returned by LSP. Closing connections...' % resp)
        lsp_comms.close_socket()
        serv_Lidar.close_socket()
        return

    # Start lidar acquisitions
    lidar_control = Popen(['.\\ultra_simple.exe'], shell=True)

    # Thread for receiving LSP data
    # lsp_q = queue.Queue()
    exit_q = queue.Queue()
    lsp_q = Queue()
    lsp_thread = threading.Thread(target=queue_lsp_data_thread, args=(lsp_comms, lsp_q, exit_q, ))       # Thread option
    # lsp_thread = Process(target=queue_lsp_data_multiprocess, args=(lsp_comms.sock, lsp_q,))     # Multiprocess option
    lsp_thread.daemon = True
    lsp_thread.start()

    # Thread for saving data
    data_q = Queue()  # Queue for data arrays
    filename_q = Queue()  # Queue for filename
    save_thread = threading.Thread(target=save_data, args=(data_q, filename_q,))        # Thread option
    # save_thread = Process(target=save_data, args=(data_q, filename_q,))               # Multiprocess option
    save_thread.daemon = True
    save_thread.start()  # Start thread for saving data

    x = 0
    message = b''  # Originally set message to empty byte string
    while 1:
        data_array = np.zeros([ArrayInfo.NUM_SCANS, ArrayInfo.len_array])                       # Create array
        filename = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S_u%f')  # Filename from data/time
        full_path_save = full_dir_path + filename                           # Full path to lidar file

        for i in range(ArrayInfo.NUM_SCANS):
            # print('Scan number: %i' % i)
            idx_lid = 0     # Lidar data point index - we increment this up as we gather lidar data
            while idx_lid < num_lidar_iter:
                # Try to get LSP scan data
                try:
                    lsp_data = lsp_q.get(block=False)
                except queue.Empty:
                    lsp_data = None
                else:
                    data_array[i, :ArrayInfo.len_lsp] = lsp_processor.extract_temp_bin(lsp_data)
                    data_array[i, ArrayInfo.speed_idx] = lsp_processor.extract_scan_speed(lsp_data)

                lidar_data = serv_Lidar.get_data()  # Try to get data
                if lidar_data is not None:

                    # Determine lidar indexes to store data in array
                    idx_start = ArrayInfo.lid_idx_start + (idx_lid * size_lid)
                    idx_end = idx_start + size_lid

                    # Store data in array
                    data_array[i, idx_start:idx_end] = lidar_data[:]

                    idx_lid += 1  # Increment lidar index

                if lsp_data is not None:
                    break  # If the try statement was successful in getting data we move on to the next LSP scan

        # Save scans
        filename_q.put(full_path_save)      # Put filename in queue first
        data_q.put(data_array)              # Then put data in queue, so filename is already there for the function

        try:
            ex = _q.get(block=False)
        except queue.Empty:
            pass
        else:
            if ex == -1:
                # Stop all processes and exit
                data_q.put(-1)  # Terminate save data thread
                exit_q.put(-1)  # Terminate LSP thread
                save_thread.join()
                lsp_thread.join()
                serv_lidar_stop.stop_lid()              # Stop lidar
                lsp_comms.stop_stream_bin()             # Stop LSP
                resp = lsp_comms.recv_stream_resp()     # Receive response to stop LSP
                if resp != 0:
                    if messages is not None:
                        messages.message('[LSP] Error stopping stream. Closing socket.')
                    else:
                        print('[LSP] Error stopping stream. Closing socket.')
                else:
                    if messages is not None:
                        messages.message('[LSP] All worked well. Closing socket.')
                    else:
                        print('[LSP] All worked well. Closing socket.')
                lsp_comms.close_socket()                    # Close socket with LSP even if we haven't stopped binary stream
                return
                # os.kill(lidar_control.pid, signal.CTRL_C_EVENT)   # Stop lidar


        # # For saving data
        # filename_lidar = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S') + '_lidar.dat'    # Filename from data/time
        # full_path_lidar = full_dir_path + filename_lidar                                       # Full path to lidar file
        # with open(full_path_lidar, 'ab') as fid_lidar:
        #     for i in range(1000):
        #         lidar_data = serv_Lidar.get_data()
        #         if lidar_data != None:
        #             time_now = datetime.datetime.now().isoformat(timespec='microseconds')
        #             save_lidar(fid_lidar, lidar_data, time_now)

                # x += 1  # Represents the scan number of the LSP data, this can be used to


def queue_lsp_data_thread(lsp_comms, lsp_q, exit_q):
    """Simple function to loop through receiving lsp data and putting it in queue"""
    while 1:
        # Check if we should exit thread
        try:
            ex = exit_q.get(block=False)
        except queue.Empty:
            pass
        else:
            if ex == -1:
                print('Exiting thread [queue_lsp_data_thread()]')
                return
            else:
                print('Unknown exit command [{0}] in queue_lsp_data_thread()'.format(ex))

        # Receive data and put into queue
        lsp_comms.recv_bin_data()
        unpacked_data = lsp_comms.parse_mess_bin()
        lsp_q.put(unpacked_data)

def queue_lsp_data_multiprocess(sock, lsp_q):
    """Simple function to loop through receiving lsp data and putting it in queue
    -> Using the function in LSP_control rather than the SocketLSP method, for multiprocessing"""
    while 1:
        unpacked_data = recv_bin_data(sock)
        lsp_q.put(unpacked_data)

def save_data(data_q, filename_q):
    """Saves data array"""
    while 1:
        array2write = data_q.get()
        if type(array2write) is not np.ndarray:   # Exit thread command
            if array2write == -1:
                print('Exiting thread [save_data()]')
                return
            else:
                print('Unrecognisable exit command: {0}'.format(array2write))
        file2write = filename_q.get()
        # np.save(file2write, array2write)
        sci.savemat(file2write + '.mat', mdict={'arr': array2write})

if __name__ == "__main__":
    handle_data()