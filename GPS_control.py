# Requires PyUSB - installed using pip install pyusb
# PyUSB is dependent on libusb-0.1 which was installed using the devel-filter executable found at:
# https://sourceforge.net/projects/libusb-win32/files/libusb-win32-releases/1.2.6.0/

import usb.core
import usb.util

devices = usb.core.find(find_all=True)
i = 1
for dev in devices:
    print(dev.idProduct, dev.idVendor, dev.bus, dev.address)
    dev.set_configuration()
    if i == 1:
        dev.write(dev.address, b'PAAG,MODE,START\r\n')
        ret = dev.read(0x81, 10, 100)
        print(ret)
    i += 1

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