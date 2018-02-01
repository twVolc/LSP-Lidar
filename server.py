# Script containing class for main data HUB and local machine networking of the lidar + LSP system
# A Server will be created, opening a socket to communicate with local programs controlling the lidar and LSP separately

import socket


class Instruments:
    SERVER_LIDAR = 0
    SERVER_LSP = 1


class SocketServ:
    """Server for local machine communications with programs acquiring data from Lidar and/or LSP"""
    def __init__(self, instrument, host='localhost'):
        self.host = host

        if instrument != Instruments.SERVER_LIDAR and instrument != Instruments.SERVER_LSP:
            print('Error instantiating class. One of the correct instruments must be given on instantiation')
            return
        self.instrument = instrument    # Tells socket if it is for Lidar or LSP

        # Create socket
        self.sock = None
        self.connected = False
        status = self.create_socket()

        # Bind to socket
        if status == 0:
            self.port = self.bind_to()

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
            print('Got connection!!!!')
        except socket.gaierror as e:
            self.connected = False
            print("Address related error connecting to server: %s" % e)
        except socket.error as e:
            self.connected = False
            print("Connection error: %s" % e)

        if self.connected:
            return self.sock.gethostname()[1]

    def save_port(self):
        """Save port number to local file so it can be accessed by other programs"""
        if self.instrument == Instruments.SERVER_LIDAR:
            instrument_str = 'Lidar'
        elif self.instrument == Instruments.SERVER_LSP:
            instrument_str = 'LSP'
        else:
            print('Error!!! Instrument is not correctly defined')
            return

        with open('network.cfg', 'w') as f:
            f.write('port_%s=%i' % (instrument_str, self.port))



if __name__ == '__main__':
    pass