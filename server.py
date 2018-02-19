# Script containing class for main data HUB and local machine networking of the lidar + LSP system
# A Server will be created, opening a socket to communicate with local programs controlling the lidar and LSP separately

import socket
import os
from queue import Empty
from threading import Thread
from multiprocessing import Process, Queue
import struct
import time
import numpy as np


class Instruments:
    """Class hold useful attributes for socket work"""
    # These enumerators are passed to SocketServ on instantiation, to define the socket type
    SERVER_LIDAR = 0
    SERVER_LSP = 1

    LSP_FMT = None
    # LIDAR_FMT = '=H I B 2c'   # Format for lidar data: distance (unsigned short), angle (float), quality (byte)
    LIDAR_FMT = 'H I B'         # Format for lidar data: distance (unsigned short), angle (float), quality (byte)
    LIDAR_DIST_IDX = 0          # Index position for location of distance
    LIDAR_ANGLE_IDX = 1         # Index position for location of angle
    LIDAR_QUAL_IDX = 2          # Index position for location of quality
    LIDAR_FLOAT_SCALE = 1e6     # Value by which the float has been scaled
    NUM_LIDAR_PTS = 3           # Number of items for each lidar set of data (i.e. distance, angle, quality)


def recv_data(_q, fmt, float_idxs, num_pts_recv):
    """Receive LSP data stream -
    function is not a class method for SocketServ because of issues with multiprocessing/pickling - it didn't like it!"""
    fmt_full = '=' + (num_pts_recv * (fmt + ' '))
    unpacker = struct.Struct(fmt_full)  # Size of message to be expected
    size_mess = struct.calcsize(fmt_full)  # Size of message to be expected
    print('Receiving messages of size: %i' % size_mess)
    data_stream = b''   # Empty message
    conn = _q.get()     # Wait for connection to be put in queue
    while 1:
        # Receive data until we exceed expected message size
        # Chances are I'm not correctly restarting te data stream so I'm looping through printing the same thing?
        bytes_left = size_mess
        while bytes_left != 0:
            data_stream += conn.recv(bytes_left)
            bytes_left = size_mess - len(data_stream)

        # Unpack message and put it in the queue
        message_unpacked = np.array(unpacker.unpack(data_stream), dtype=np.float32)
        message_unpacked[float_idxs] /= Instruments.LIDAR_FLOAT_SCALE  # Convert back to float
        _q.put(message_unpacked)
        data_stream = b''

class SocketServ:
    """Server for local machine communications with programs acquiring data from Lidar and/or LSP"""
    def __init__(self, instrument, host='localhost'):
        self.num_pts_recv = 1           # Number of lidar datasets to receive and package in one go
        # Calculate indices where lidar angles (floats) are located, for converting back to float later
        self.float_idxs = np.arange(Instruments.LIDAR_ANGLE_IDX, Instruments.NUM_LIDAR_PTS * self.num_pts_recv,
                                    Instruments.NUM_LIDAR_PTS)

        self._queue = Queue()  # Instantiate Queue object
        self.host = host
        self.conn = None        # Connection
        self.addr = None        # Address of connection

        if instrument != Instruments.SERVER_LIDAR and instrument != Instruments.SERVER_LSP:
            print('Error instantiating class. One of the correct instruments must be given on instantiation')
            return
        self.instrument = instrument    # Tells socket if it is for Lidar or LSP

        # Create network directory to hold anything necessary
        self.work_dir = '.\\network\\'
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)

        # Create socket
        self.sock = None
        self.connected = False
        status = self.create_socket()

        # Bind to socket
        if status == 0:
            self.port = self.bind_to()

        # Save port name
        self.save_port()

        # Listen for a connection and accept if it comes in - threaded so that we don't pause listening for connection
        self._t_conn = Thread(target=self.get_connection, args=())
        self._t_conn.daemon = True
        self._t_conn.start()

        # Start receive thread
        if self.instrument == Instruments.SERVER_LSP:
            self._t = Thread(target=self.recv_data, args=(self._queue, Instruments.LSP_FMT,))
        elif self.instrument == Instruments.SERVER_LIDAR:
            self._t = Thread(target=self.recv_data, args=(self._queue, Instruments.LIDAR_FMT,))
            # self._t = Process(target=recv_data, args=(self._queue, Instruments.LIDAR_FMT,
            #                                           self.float_idxs, self.num_pts_recv,))  # Multiprocessing attempt

        self._t.daemon = True       # Set daemon so it is killed on exit
        self._t.start()

    def create_socket(self):
        """Create socket object"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print('Socket created!')
            return 0
        except socket.error as e:
            print('Error creating socket: %s' % e)
            return -1

    def bind_to(self):
        """Bind socket"""
        try:
            self.sock.bind((self.host, 0))
            self.connected = True
            print('Bound to socket!')
        except socket.gaierror as e:
            self.connected = False
            print("Address related error connecting to server: %s" % e)
        except socket.error as e:
            self.connected = False
            print("Connection error: %s" % e)

        if self.connected:
            return self.sock.getsockname()[1]
        else:
            return -1

    def close_socket(self):
        """Close socket"""
        self.sock.close()

    def save_port(self):
        """Save port number to local file so it can be accessed by other programs"""
        if self.instrument == Instruments.SERVER_LIDAR:
            instrument_str = 'Lidar'
        elif self.instrument == Instruments.SERVER_LSP:
            instrument_str = 'LSP'
        else:
            print('Error!!! Instrument is not correctly defined')
            return

        line = 'port=%i' % self.port
        save_path = self.work_dir + ('network_%s.cfg' % instrument_str)

        with open(save_path, 'w') as f:
            f.write(line)

    def get_connection(self):
        """Wait for client connection and then accept it"""
        # Wait for connection
        print('Listening on port %i...' % self.port)
        self.sock.listen(1)

        # Accept connection
        self.conn, self.addr = self.sock.accept()
        print('Got connection from %s' % self.addr[0])
        self._queue.put(self.conn)

    def recv_data(self, _q, fmt):
        """Receive LSP or Lidar data stream"""
        fmt_full = self.__gen_fmt_str__(fmt)
        unpacker = struct.Struct(fmt_full)  # Size of message to be expected
        size_mess = struct.calcsize(fmt_full)  # Size of message to be expected
        print('Receiving messages of size: %i' % size_mess)
        data_stream = b''       # Empty message
        self.conn = _q.get()    # Get connection when it has been made
        while 1:
            # Receive data until we exceed expected message size
            # Chances are I'm not correctly restarting te data stream so I'm looping through printing the same thing?
            bytes_left = size_mess
            while bytes_left != 0:
                try:
                    data_stream += self.conn.recv(bytes_left)
                except ConnectionResetError:
                    print('Lidar closed connection. Data stream terminated')
                    return
                bytes_left = size_mess - len(data_stream)

            # Unpack message and put it in the queue
            message_unpacked = np.array(unpacker.unpack(data_stream), dtype=np.float32)
            message_unpacked[self.float_idxs] /= Instruments.LIDAR_FLOAT_SCALE  # Convert back to float
            _q.put(message_unpacked)
            data_stream = b''

    def __gen_fmt_str__(self, fmt):
        """Generate format string for struct unpacking
        May be obsolete now that recv_data has been moved outside of class"""
        return '=' + (self.num_pts_recv * (fmt + ' '))


    def get_data(self):
        """Pulls data from the queue and returns it
        Queue is non-blocking so that if there is no data we return None"""
        try:
            data = self._queue.get(block=False)
        except Empty:
            data = None
        return data


if __name__ == '__main__':
    serv_Lidar = SocketServ(Instruments.SERVER_LIDAR)
    while 1:
        time.sleep(10)
        print(serv_Lidar.get_data())
