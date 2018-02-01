from read_lidar import read_lidar
from process_lidar import LidarProcess
from LSP_control import ProcessLSP
import matplotlib.pyplot as plt

# RPLIDAR's viewing side when attached to LSP-HD is 0-180 degrees, so 90 degrees is in line with centre of LSP-HD

filename = 'C:\\Users\\tw9616\\Documents\\PhD\\EE Placement\\Lidar\\RPLIDAR_A2M6\\VC2017 Test\\sdk\\output\\win32\\Release\\2018-01-31\\2018-01-31_T105420.dat'

GPS_origin = [(1, 28, 51.79), (53, 22, 53.42)]   # GPS coordinates of origin (church) [53°22'54.42"N,   1°28'51.79"W]


# Read in lidar data
lidar_data = read_lidar(filename)

# Instantiate main processing class with data
process_lidar = LidarProcess(lidar_data)

# Extract data from dictionaries, so that they are assigned to attributes
process_lidar.extract_all()

# Removes data with 0 quality
process_lidar.remove_bad_data()

# Extract between two angles
process_lidar.extract_between(40, 140)

# Plot data in instance
process_lidar.draw_plot()

# Split data up into separate scans
sep_scans = process_lidar.split_scans()
print(sep_scans[7]["quality"])
print(sep_scans[7]["angle"])


temps_file = 'C:\\Users\\tw9616\\Documents\\PhD\\EE Placement\\LSP-HD\\Data\\2018-01-31\\2018-01-31_105447_temperatures.npy'
speed_file = 'C:\\Users\\tw9616\\Documents\\PhD\\EE Placement\\LSP-HD\\Data\\2018-01-31\\2018-01-31_105447_speeds.npy'
lsp_process = ProcessLSP()
temperatures = lsp_process.read_array(temps_file)
speeds = lsp_process.read_array(speed_file)

num_scans = temperatures.shape[0]

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