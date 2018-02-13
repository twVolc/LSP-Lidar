from LSP_control import *
import numpy as np
import matplotlib.pyplot as plt
import datetime
import os

lsp_processor = ProcessLSP()  # Instantiate object to process data
lsp_comms = SocketLSP('10.1.10.1')  # Instantiate communications object
lsp_comms.init_comms()
message = lsp_comms.recv_resp()

num_scans = 1000
temperatures = np.zeros([num_scans, 1000])      # Array to hold temperature data
scan_speeds = np.zeros([num_scans])             # Array to hold all of the scan speeds

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
message = b''      # Originally set message to empty byte string
for i in range(num_scans):
    print('Receiving message %i' % i)
    lsp_comms.recv_bin_data()   # Receive data

    # Unpack scan and then extract temperatures
    unpacked_data = lsp_comms.parse_mess_bin()
    temperatures[i, :] = lsp_processor.extract_temp_bin(unpacked_data)
    scan_speeds[i] = lsp_processor.extract_scan_speed(unpacked_data)

    print(lsp_comms.scan_message)
    print(lsp_processor.extract_scan_speed(unpacked_data))

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



# ============================================================
# SAVE DATA TO DISK
# ============================================================
data_path = 'C:\\Users\\tw9616\\Documents\\PhD\\EE Placement\\LSP-HD\\Data\\'
date_dir = datetime.datetime.now().strftime('%Y-%m-%d')
full_dir_path = data_path + date_dir + '\\'
# Create directory for data if it doesn't already exist
if not os.path.exists(full_dir_path):
    os.makedirs(full_dir_path)

# Generate filename with time and date
filename = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
full_file_path = full_dir_path + filename

# Save temperatures and scan speed arrays
print('Saving temperature array...')
np.save(full_file_path + '_temperatures', temperatures)
print('Saving scan speeds...')
np.save(full_file_path + '_speeds', scan_speeds)
# =============================================================

fig = plt.figure()
ax = fig.add_subplot(111)
for i in range(num_scans):
    ax.plot(temperatures[i,:])
ax.set_ylabel('Temperature [oC]')
ax.set_xlabel('Scan position')

fig_2 = plt.figure()
ax_2 = fig_2.add_subplot(111)
ax_2.plot(temperatures[:, 500])
ax_2.set_ylabel('Temperature [oC]')
ax_2.set_xlabel('Scan position')
plt.show()