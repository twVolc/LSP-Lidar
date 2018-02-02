# Script containing class for main data HUB and local machine networking of the lidar + LSP system
# A Server will be created, opening a socket to communicate with local programs controlling the lidar and LSP separately

import socket
import os
from queue import Queue, Empty
from threading import Thread
import struct


class Instruments:
    """Class hold useful attributes for socket work"""
    # These enumerators are passed to SocketServ on instantiation, to define the socket type
    SERVER_LIDAR = 0
    SERVER_LSP = 1

    LSP_FMT = None
    LIDAR_FMT = '=H I B'        # Format for lidar data: distance (unsigned short), angle (float), quality (byte)
    LIDAR_FLOAT_SCALE = 1e6     # Value by which the float has been scaled


class SocketServ:
    """Server for local machine communications with programs acquiring data from Lidar and/or LSP"""
    def __init__(self, instrument, host='localhost'):
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

        # Listen for a connection and accept it if it comes in
        self.get_connection()

        # Once it has a connection, start receiving data in thread
        self._queue = Queue()       # Instantiate Queue object

        if self.instrument == Instruments.SERVER_LSP:
            self._t = Thread(target=self.recv_data, args=(self._queue, Instruments.LSP_FMT,))
        elif self.instrument == Instruments.SERVER_LIDAR:
            self._t = Thread(target=self.recv_data, args=(self._queue, Instruments.LIDAR_FMT,))
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

    def recv_data(self, _q, fmt):
        """Receive LSP data stream"""
        unpacker = struct.Struct(fmt)       # Size of message to be expected
        size_mess = struct.calcsize(fmt)    # Size of message to be expected
        print(size_mess)
        data_stream = b''  # Empty message
        while 1:
            # Receive data until we exceed expected message size
            while len(data_stream) < size_mess:
                data_stream += self.conn.recv(size_mess)

            # Split received data to extract message
            message = data_stream[0:size_mess]

            # Any additional bytes are put back into data stream
            data_stream = message[size_mess:]

            # Unpack message and put it in the queue
            message_unpacked = list(unpacker.unpack(message))
            message_unpacked[1] /= Instruments.LIDAR_FLOAT_SCALE   # Convert back to float
            _q.put(message_unpacked)

    def get_data(self):
        """Pulls data from the queue and returns it"""
        data = self._queue.get()
        return data


# '''External class - possibly take ideas from this'''
# class NonBlockingStreamReader:
#
#     def __init__(self, stream):
#         '''
#         stream: the stream to read from.
#                 Usually a process' stdout or stderr.
#         '''
#
#         self._s = stream
#         self._q = Queue()
#
#         def _populateQueue(stream, queue):
#             '''
#             Collect lines from 'stream' and put them in 'quque'.
#             '''
#
#             while True:
#                 line = stream.readline()
#                 if line:
#                     queue.put(line)
#                 else:
#                     raise UnexpectedEndOfStream
#
#         self._t = Thread(target = _populateQueue,
#                 args = (self._s, self._q))
#         self._t.daemon = True
#         self._t.start() #start collecting lines from the stream
#
#     def readline(self, timeout = None):
#         try:
#             return self._q.get(block = timeout is not None,
#                     timeout = timeout)
#         except Empty:
#             return None
#
#
# class UnexpectedEndOfStream(Exception):
#     pass


if __name__ == '__main__':
    serv_LSP = SocketServ(Instruments.SERVER_LIDAR)
    while 1:
        print(serv_LSP.get_data())
