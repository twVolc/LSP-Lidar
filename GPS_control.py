# Requires PyUSB - installed using pip install pyusb
# PyUSB is dependent on libusb-0.1 which was installed using the devel-filter executable found at:
# https://sourceforge.net/projects/libusb-win32/files/libusb-win32-releases/1.2.6.0/


# ----------------------------------------------------------------------
# PySerial tests
# ----------------------------------------------------------------------
import serial
import io

gps_baud = 9600

command = 'PAAG,MODE,START\r\n'
command_id = 'PAAG,ID\r\n'.encode()

ser = serial.Serial(port='COM4', baudrate=gps_baud, stopbits=serial.STOPBITS_TWO)
print(ser.parity)
ser.write(command_id)
print('Sent command: {}'.format(command_id))
line = ser.read()
print('Received data: {}'.format(line))

# sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
#
# sio.write(command.decode('utf-8'))
# sio.flush()     # it is buffering. required to get the data out *now*
# hello = sio.readline()
# print(hello)


# # -------------------------------------------------------------------------------------------
# # PYUSB tests - currently unsuccessful
# # --------------------------------------------------------------------------------------------
# import usb.core
# import usb.util
#
# VENDOR_ID = 0x0403      # Vendor ID for GPS device
# PRODUCT_ID = 0xe8db     # Product ID for GPS device
#
# command = b'PAAG,MODE,START\r\n'
# command_id = b'PAAG,ID\r\n'
#
# devices = usb.core.find(find_all=True, idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
#
#
# i = 0
# for dev in devices:
#     # dev.set_configuration()
#     # data = dev.ctrl_transfer(0b10100001, 0x01, 3<<8, 0, 4)
#     # print(data)
#
#     # print(dev)
#     print(dev.idProduct, dev.idVendor, dev.bus, dev.address)
#     if i == 0:
#         dev.set_configuration()
#         interface = 0
#         endpoint = dev[0][(0,0)][0]
#         print(endpoint)
#
#         dev.write(dev.address, command)
#         ret = dev.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize)
#         # ret = dev.read(1, 100)
#         # ret = dev.read(0x81, 10, 100)
#         print(ret)
#     i += 1

# # set the active configuration. With no arguments, the first
# # configuration will be the active one
# devices.set_configuration()
#
# # get an endpoint instance
# cfg = devices[0].get_active_configuration()
# intf = cfg[(0,0)]
#
# ep = usb.util.find_descriptor(
#     intf,
#     # match the first OUT endpoint
#     custom_match = \
#     lambda e: \
#         usb.util.endpoint_direction(e.bEndpointAddress) == \
#         usb.util.ENDPOINT_OUT)
#
# assert ep is not None
#
# # write the data
# ep.write(b'PAAG,MODE,START\r\n')