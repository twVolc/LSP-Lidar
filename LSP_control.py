import socket
import time
import struct
import threading
import sys
import time
import numpy as np
import scipy.io as sci

class SocketLSP:
    """Classs to interface with LSP -> send + recieve data -> parse data to useful output"""
    def __init__(self, hostIP, lspIP = '10.1.10.100'):
        self.port = 1050            # LSP-HD listening port
        self.hostIP = hostIP
        self.lspIP = lspIP

        self.current_mess_byte = b''                # Byte current message
        self.current_mess = ''                      # Holds any incomplete message
        self.scan_message = None                    # Will hold a scan binary message
        self.message_incomplete = False             # Used to check if we need to receive more data

        # Define important LSP-HD paramters
        self.reconnect_delay = 6                            # Allow 6 seconds before attempting reconnect
        self.end_mess = '\r\x00'                            # End of message bytes (<CR><NULL>)
        self.end_mess_bytes = b'\r\0'                       # End of message bytes (<CR><NULL>)
        self.end_mess_len = len(self.end_mess)              # Length of end message, for extracting string in message
        self.good_resp = b'RUP 0' + self.end_mess_bytes     # Reply code when all is good

        # Define binary format string. Whitespace is ignored in format specifiers, but is included for clarity
        self.encoding = 'utf-8'                                             # Encoding of ascii messages
        self.bin_header_size = 7                                            # Data needed for header info
        self.fmt_header = '=3c H h'                                          # HEader format
        self.fmt_bin = '=3c H h 6H h 6h 6H 6h f 3H 29h 8f 43h 1000h 2c'     # Binary data format
        self.bin_unpacker = struct.Struct(self.fmt_bin)                     # Create structure from format string
        self.bin_data_len = struct.calcsize(self.fmt_bin)                   # How much data is expected from scan

        # Create socket
        self.sock = None
        self.connected = False
        status = self.create_socket()

        # Connect to the LSP-HD
        if status == 0:
            self.connect_to()

    def create_socket(self):
        """Create a socket"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print('Socket created!')
            return 0
        except socket.error as e:
            print('Error creating socket: %s' % e)
            return -1

    def connect_to(self):
        """Connect to server"""
        try:
            self.sock.connect((self.lspIP, self.port))
            self.connected = True
            print('Got connection!!!!')
        except socket.gaierror as e:
            self.connected = False
            print("Address related error connecting to server: %s" % e)
        except socket.error as e:
            self.connected = False
            print("Connection error: %s" % e)

    def close_socket(self):
        """Close socket"""
        self.sock.close()
        print('Closed socket!!!')

    def attempt_reconnect(self):
        """Attempt to reconnect to dropped server"""
        time.sleep(self.reconnect_delay)
        self.connect_to()

    def init_comms(self):
        """Send initial Hello command to start communications"""
        mess = b'SHO' + self.end_mess_bytes
        self.sock.sendall(mess)

    def recv_resp_simple(self, bytes=1024):
        """Simply recieve the message and return it, don't do anything to it"""
        mess = self.sock.recv(bytes)
        print('Got message of length: %i byte(s)' % len(mess))
        return mess

    def recv_stream_resp(self):
        """Specifically receives the LSP reply from a stream response, and flags if there are issues"""
        return_mess = b''
        while True:
            return_mess += self.recv_resp_simple(1)
            if return_mess[-2:] == self.end_mess_bytes:
                mess_ascii = return_mess.decode(self.encoding)
                return_code = int(mess_ascii[-3])
                if return_code == 0:
                    print('LSP response - all good!')
                else:
                    print('LSP-HD error code: %i' % return_code)
                return return_code

    def recv_bin_data(self):
        """Receive binary message"""
        mess = self.current_mess_byte

        # Receive data until we have a full header
        mess_current_length = len(mess)
        while mess_current_length < self.bin_header_size:
            mess += self.sock.recv(self.bin_header_size)    # Receive the header
            mess_current_length = len(mess)                 # Current length of the message

        # Check error code in header
        header = struct.unpack(self.fmt_header, mess)
        error_code = header[-1]
        # If bad error code, close socket and return
        if error_code != 0:
            print('LSP providing error code of %i. Communication terminated!' %i)
            self.close_socket()
            return

        # If error code is good, find size of message
        mess_len_total = header[-2]

        # Loop to receive bytes until we have the entire message
        while mess_current_length < mess_len_total:
            bytes_left = mess_len_total - mess_current_length       # How many more bytes need to be received
            mess += self.sock.recv(bytes_left)                      # Try to receive those bytes
            mess_current_length = len(mess)                         # Current length of the message

        if mess_current_length > mess_len_total:
            print('Warning! More bytes received than expected')     # Warning if we have too much data
            # If we have more data than a single message, extract the single scan and add rest of data to 'message'
            self.current_mess_byte = mess[mess_len_total:]
            complete_scan = mess[:mess_len_total]
            # Otherwise the complete scan is just equal to the whole message
        else:
            complete_scan = mess
            self.current_mess_byte = b''

        self.scan_message = complete_scan

    def recv_resp(self):
        """Receive repsonse from LSP-HD"""
        total_message = self.current_mess       # Get any current data yet to be fully extracted with end char
        mess = []                               # Empty list to append separate messages to
        while True:
            data = None
            # Receive data from socket
            while data is None:
                data = self.sock.recv(1024)

            print(data)
            total_message += data.decode(self.encoding)

            # Search for end of message characters
            end_idx = total_message.find(self.end_mess)
            # while end_idx > -1:
            #     # Extract message
            #     cut_idx = end_idx + self.end_mess_len
            #     mess = mess.append(total_message[0:cut_idx])
            #     print(mess)
            #
            #     if mess != len(total_message):
            #         total_message = total_message[cut_idx:]
            #         self.current_mess = total_message               # Set current message to rest of message
            #
            #         # Search for again end of message characters
            #         end_idx = total_message.find(self.end_mess)     # If found, the while loop will iterate again
            #         if end_idx == -1:
            #             print('Returning message with some data incomplete')
            #             print(mess)
            #             return mess     # If no end_mess is found - return mess -> extra data stored in current_mess
            #
            #     else:
            #         self.current_mess = ''      # Set current message to empty string if all data was used up
            #         print('Returning message and all messages are complete')
            #         return mess                 # Return the message
            if end_idx != -1:
                # Only one message at a time should ever be sent, so there will never be a need to split the messages
                # into more than one message. Therefore we can just return the message.
                return total_message[:end_idx]
            else:
                self.current_mess = total_message
                print('Incomplete message received')
                self.message_incomplete = True          # Set this flag to true, so we know to receive more data

    def req_scan_bin(self):
        """Request binary scan data SBD<CR><NULL>"""
        message = b'SBD' + self.end_mess_bytes
        print('Requesting scan...')
        self.sock.sendall(message)

    def req_stream_bin(self):
        """Request stream of scans to be sent"""
        meassage = b'SUP 23 1' + self.end_mess_bytes
        print('Requesting binary stream...')
        self.sock.sendall(meassage)

    def stop_stream_bin(self):
        """Stop stream of scan data"""
        meassage = b'SUP 23 0' + self.end_mess_bytes
        print('Stopping binary stream...')
        self.sock.sendall(meassage)

    def parse_mess_ASCII(self, mess):
        """Parse LSP message -> message must be sent in ASCII format"""
        # Decode message - possibly not necessary if we are doing this in the receiving stage
        mess_str = mess.decode(self.encoding)

        # Extract individual data-points into list
        mess_list = mess_str.split(' ')

        mess_type = mess_list[0]

        # Maybe do more with this function, or perhaps just do these basics, and let further processing be done once the response type is known
        return mess_type, mess_list

    def parse_mess_bin(self):
        """Parse LSP message -> message must be from the binary data option"""
        unpacked_mess = self.bin_unpacker.unpack(self.scan_message)      # Unpack message data
        len_mess = unpacked_mess[3]                         # Length of message as defined within the message
        if len_mess != len(self.scan_message):
            print('Warning!!! Expected message of length %i bytes but got message of %i bytes' % (len_mess, len(self.scan_message)))
        return unpacked_mess

class LSPInfo:
    """Used by recv_bin_data()
    Should be able to inherit this in SocketLSP to save writing things twice?"""
    port = 1050  # LSP-HD listening port

    current_mess_byte = b''  # Byte current message
    current_mess = ''  # Holds any incomplete message
    scan_message = None  # Will hold a scan binary message
    message_incomplete = False  # Used to check if we need to receive more data

    # Define important LSP-HD paramters
    reconnect_delay = 6  # Allow 6 seconds before attempting reconnect
    end_mess = '\r\x00'  # End of message bytes (<CR><NULL>)
    end_mess_bytes = b'\r\0'  # End of message bytes (<CR><NULL>)
    end_mess_len = len(end_mess)  # Length of end message, for extracting string in message
    good_resp = b'RUP 0' + end_mess_bytes  # Reply code when all is good

    # Define binary format string. Whitespace is ignored in format specifiers, but is included for clarity
    encoding = 'utf-8'  # Encoding of ascii messages
    bin_header_size = 7  # Data needed for header info
    fmt_header = '=3c H h'  # HEader format
    fmt_bin = '=3c H h 6H h 6h 6H 6h f 3H 29h 8f 43h 1000h 2c'  # Binary data format
    bin_unpacker = struct.Struct(fmt_bin)  # Create structure from format string
    bin_data_len = struct.calcsize(fmt_bin)  # How much data is expected from scan


def recv_bin_data(sock):
    """Receive binary message - function rather than class  - for multiprocessing"""
    mess = b''

    # Receive data until we have a full header
    mess_current_length = len(mess)
    while mess_current_length < LSPInfo.bin_header_size:
        mess += sock.recv(LSPInfo.bin_header_size)  # Receive the header
        mess_current_length = len(mess)  # Current length of the message

    # Check error code in header
    header = struct.unpack(LSPInfo.fmt_header, mess)
    error_code = header[-1]
    # If bad error code, close socket and return
    if error_code != 0:
        print('LSP providing error code of %i. Communication terminated!' % i)
        sock.close()
        return

    # If error code is good, find size of message
    mess_len_total = header[-2]

    # Loop to receive bytes until we have the entire message
    while mess_current_length < mess_len_total:
        bytes_left = mess_len_total - mess_current_length  # How many more bytes need to be received
        mess += sock.recv(bytes_left)  # Try to receive those bytes
        mess_current_length = len(mess)  # Current length of the message

    if mess_current_length > mess_len_total:
        print('Warning! More bytes received than expected')  # Warning if we have too much data
        # If we have more data than a single message, extract the single scan and add rest of data to 'message'
        complete_scan = mess[:mess_len_total]
    # Otherwise the complete scan is just equal to the whole message
    else:
        complete_scan = mess

    unpacked_mess = LSPInfo.bin_unpacker.unpack(complete_scan)  # Unpack message data

    return unpacked_mess


class ProcessLSP:
    """Class for processing LSP data"""
    def __init__(self):
        self.start_temp_idx = -1002     # Index to start extracting temperature in unpacked binary message
        self.end_temp_idx = -2          # Index to stop extracting temperature
        self.scan_speed_idx = 30        # Index of scan speed in unpacked binary message

    def extract_temp_bin(self, mess):
        """Extracts scan temperatures from message tuple and converts to actual temperature"""
        temperatures = np.asarray(mess[self.start_temp_idx:self.end_temp_idx])  # Convert to numpy array
        temperatures = temperatures / 10.0                                      # Convert to temperature
        return temperatures

    def extract_scan_speed(self, mess):
        """Extracts the scanner speed from message tuple"""
        scan_speed = mess[self.scan_speed_idx]
        return scan_speed

    def save_scan(self, filename, data_array):
        with open(filename, 'wb') as f:
            f.write(data_array)
        print('Data saved!!')

    def read_array(self, filename):
        """Read in the numpy temperature file and return array"""
        extension = filename.split('.')[-1]     # Get file extension
        if extension == 'mat':
            array = sci.loadmat(filename)
        elif extension == 'npy':
            array = np.load(filename)
        else:
            print('Error!!! Unrecognised file type for read_array()')
            array = None
        return array

if __name__ == "__main__":
    # Set up comms and processing objects
    lsp_processor = ProcessLSP()            # Instantiate object to process data
    lsp_comms = SocketLSP('10.1.10.1')      # Instantiate communications object
    lsp_comms.init_comms()
    # recv_thread = threading.Thread(target=lsp.recv_resp, args=())
    # recv_thread.start()
    message = lsp_comms.recv_resp()

    # ------------------
    # single scan tests
    print(message)
    lsp_comms.req_scan_bin()
    message = lsp_comms.recv_resp_simple(5000)
    print(message)
    lsp_comms.scan_message = message
    unpacked_mess = lsp_comms.parse_mess_bin()
    print(unpacked_mess)

    extracted_temp = lsp_processor.extract_temp_bin(unpacked_mess)
    print(extracted_temp)
    print(unpacked_mess[-2:])
    # ----------------------

    # ===========================================
    # Byte Stream
    # ===========================================
    lsp_comms.req_stream_bin()
    resp = lsp_comms.recv_stream_resp()
    if resp != 0:
        lsp_comms.close_socket()
        sys.exit()

    # Test time
    start_time = time.time()

    # Receive constant stream of bytes
    num_scans = 100
    message = b''      # Originally set message to empty byte string
    for i in range(num_scans):
        # print('Receiving message %i' % i)
        lsp_comms.recv_bin_data()   # Receive data

        print(lsp_comms.scan_message)

    # Elapsed time
    print('Elapsed time for %i scans: %.2f' % (num_scans, time.time()-start_time))

    lsp_comms.stop_stream_bin()
    resp = lsp_comms.recv_stream_resp()
    if resp != 0:
        print('Error stopping stream. Closing socket.')
    else:
        print('All worked well. Closing socket.')
    lsp_comms.close_socket()
    # ============================================
