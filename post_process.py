from LSP_control import ProcessLSP
from server import Instruments
import matplotlib.pyplot as plt
import os
from data_handler import ArrayInfo
import numpy as np
import sys


class ProcessInfo:
    """Contains properties used in post-processing data"""
    LIDAR_LSP_DIST = 0.11   # Distance between Lidar and LSP acquisition positions (metres)

    # Define array to hold all of the data
    NUM_Z_DIM = 3           # Number of z-dimensions (Currently: Temperature/Distance/Angle)
    TEMP_IDX = 0            # Index for z dimension where temperature information is stored
    DIST_IDX = 1            # Index for z dimension where distance information is stored
    ANGLE_IDX = 2           # Index for z dimension where angle information is stored

    # Generate 1D array holding angles of LSP data points
    _range_lsp_angle = 80                   # Range of angles measured by LSP
    LSP_ANGLES = np.linspace(0, _range_lsp_angle, ArrayInfo.len_lsp) - (_range_lsp_angle / 2)
    LSP_MIN_ANGLE = np.min(LSP_ANGLES) - 0.5    # Angles outside of this range are discarded
    LSP_MAX_ANGLE = np.max(LSP_ANGLES) + 0.5    # Angles outside of this range are discarded
    LIDAR_ANGLE_OFFSET = -90                # Shift applied to lidar angles to match with LSP

    # Define method of interpolation for lidar measurements
    # Time interpolation takes data from lidar and spreads it evenly across contemporaneous LSP scan, regardless of scan angle
    # Angle interpolation matches angles on lidar to angles on LSP
    TIME_INTERP = False         # User can change this value (True/False)
    if not TIME_INTERP:
        ANGLE_INTERP = True
    else:
        ANGLE_INTERP = False


def interpolate_data(lidar_data, temps_dist):
    EMPTY_LID_FLAG = np.zeros([ArrayInfo.NUM_SCANS])    # Array holding flags if lidar data is empty for that scan
    lid_scan_size = lidar_data.shape[1]                 # Number of elements avaailable for lidar data per LSP scan
    distance_idxs = np.arange(Instruments.LIDAR_DIST_IDX, lid_scan_size, Instruments.NUM_LIDAR_PTS)     # Indices for extraction of all distance data points per scan line
    angle_idxs = np.arange(Instruments.LIDAR_ANGLE_IDX, lid_scan_size, Instruments.NUM_LIDAR_PTS)       # As above
    quality_idxs = np.arange(Instruments.LIDAR_QUAL_IDX, lid_scan_size, Instruments.NUM_LIDAR_PTS)      # As above

    # -----------------------------------------------------------------------------------------------------------------
    # First iterations, find where lidar data is and put it into array with indices corresponding to a temperature
    for scan in range(ArrayInfo.NUM_SCANS):
        print('Processing scan %i of %i' % (scan + 1, ArrayInfo.NUM_SCANS))
        # Iterate through the scans assigning a distance and angle to each temperature measurement
        # Need to interpolate across a scan where necessary by finding the number of lidar points for that scan line
        # Also need to interpolate between scans where no lidar data is found
        distances = lidar_data[scan, distance_idxs]
        angles = lidar_data[scan, angle_idxs] + ProcessInfo.LIDAR_ANGLE_OFFSET  # Apply offset to angles to match LSP
        quality = lidar_data[scan, quality_idxs]

        # Find where data stops
        try:
            cut_idx = np.where(quality == 0)[0][0]
            # Extract the data
        except IndexError:
            # If we have data right to the end we use all of it (distances and angles are already a defined np.array
            pass
        else:
            distances = distances[:cut_idx]
            angles = angles[:cut_idx]

        num_dat = len(distances)    # How many datapoints we have for this scan
        if num_dat == 0:
            EMPTY_LID_FLAG[scan] = 1    # Flag that we have no data for this scan
            continue
        else:

            if ProcessInfo.TIME_INTERP:
                # Find how to spread lidar data points across scan
                spread_dat = int(np.floor(ArrayInfo.len_lsp / (num_dat + 1)))

                for i in range(num_dat):
                    if (angles[i] + 1) > ProcessInfo.LSP_MAX_ANGLE or (angles[i] + 1) < ProcessInfo.LSP_MIN_ANGLE:
                        EMPTY_LID_FLAG[scan] = 1  # Flag that we have no data for this scan
                        continue  # Ignore measurements outside of the FOV of the LSP
                    idx = (i + 1) * spread_dat                                  # Index for placing value
                    temps_dist[scan, idx, ProcessInfo.DIST_IDX] = distances[i]  # Assign distance value
                    temps_dist[scan, idx, ProcessInfo.ANGLE_IDX] = angles[i]    # Assign angle value

            elif ProcessInfo.ANGLE_INTERP:
                # Loop through angles and assign data to the specific angle it corresponds to in the LSP scan
                for i in range(num_dat):
                    if (angles[i] + 1) > ProcessInfo.LSP_MAX_ANGLE or (angles[i] + 1) < ProcessInfo.LSP_MIN_ANGLE:
                        EMPTY_LID_FLAG[scan] = 1  # Flag that we have no data for this scan
                        continue    # Ignore measurements outside of the FOV of the LSP
                    idx = np.argmin(abs(ProcessInfo.LSP_ANGLES - angles[i]))
                    # print(idx)

                    # Assigning distance value with padding (5 temperature points are assigned the same distance)
                    # Done because the angular resolution of the LSP far exceeds that of the lidar
                    # Values at edge of FOV are padded differently (don't need to have specific assignments for upper
                    # indices of array because over assignment of indices just gets ignored in python
                    if idx == 0:
                        temps_dist[scan, idx:idx+3, ProcessInfo.DIST_IDX] = distances[i]    # Assign distance value
                        temps_dist[scan, idx:idx+3, ProcessInfo.ANGLE_IDX] = angles[i]      # Assign angle value
                    elif idx == 1:
                        temps_dist[scan, idx - 1:idx + 3, ProcessInfo.DIST_IDX] = distances[i]  # Assign distance value
                        temps_dist[scan, idx - 1:idx + 3, ProcessInfo.ANGLE_IDX] = angles[i]    # Assign angle value
                    else:
                        temps_dist[scan, idx - 2:idx + 3, ProcessInfo.DIST_IDX] = distances[i]  # Assign distance value
                        temps_dist[scan, idx - 2:idx + 3, ProcessInfo.ANGLE_IDX] = angles[i]    # Assign angle value

            else:
                print('Error! Processing method [in <class>ProcessInfo] incorrectly defined.')
                sys.exit()


    # ------------------------------------------------------------------------------------------------------------------
    # Iterating loop where we loop through finding the next data point available, we then perform
    # A linear interpolation between these 2 data points and set all values between from this - then move onto the next
    # Gap of data points
    # has_vals = np.nonzero(temps_dist[:, :, ProcessInfo.ANGLE_IDX])    # Array for all non-zero elements - where we have lidar data - we use angle not distance in case a true distance reading is exactly 0
    #
    # if ProcessInfo.ANGLE_INTERP:
    #     print('Performing angle interpolation...')
    #     # Interpolate distance across the same angles - may find that the delay is too large in this data (not enough
    #     # Data points, but it is worth trying)
    #     unique_cols = np.unique(has_vals[1])
    #     for col in unique_cols:
    #         # Find all places where there is a distance value in column col
    #         all_idxs = np.where(has_vals[1] == col)[0]
    #
    #         # Loop through interpolating between values
    #         num_iter = len(all_idxs) - 1
    #         for i in range(num_iter):
    #             idx_1 = all_idxs[i]
    #             idx_2 = all_idxs[i+1]
    #
    #             val_1 = temps_dist[has_vals[0][idx_1], col, ProcessInfo.DIST_IDX]
    #             val_2 = temps_dist[has_vals[0][idx_2], col, ProcessInfo.DIST_IDX]
    #
    #             scan_dif = (has_vals[0][idx_2] - has_vals[0][idx_1])    # Number of scans apart
    #             if scan_dif <= 1:
    #                 print('No interpolation required at row %i of column %i' % (i, col))
    #                 continue
    #
    #             grad = (val_2 - val_1) / scan_dif                       # Gradient for linear fit to data
    #
    #             elements = (np.arange(scan_dif) * grad) + val_1
    #             elements = elements[1:]  # Don't use first element as it would replace the distance value we already have
    #
    #             # Assign interpolated distances to array, values above and below known points are assigned the last known value
    #             temps_dist[(has_vals[0][idx_1] + 1):has_vals[0][idx_2], col, ProcessInfo.DIST_IDX] = elements
    #             temps_dist[:has_vals[0][idx_1], col, ProcessInfo.DIST_IDX] = val_1
    #             temps_dist[(has_vals[0][idx_2]+1):, col, ProcessInfo.DIST_IDX] = val_2
    #             # Assign this column and angle index so that the next has_vals check returns the right result
    #             temps_dist[:, col, ProcessInfo.ANGLE_IDX] = temps_dist[has_vals[0][idx_1], col, ProcessInfo.ANGLE_IDX]

    # After angle interp (if requested) we fill in the rest of the array by interp across scan
    # Probably should adjust distance for change in angle here - especially if using ANGLE_INTERP
    has_vals = np.nonzero(temps_dist[:, :, ProcessInfo.ANGLE_IDX])    # Array for all non-zero elements - where we have lidar data

    num_of_interp = len(has_vals[0]) - 1    # Number of interpoaltions needed
    count = 0  # Lines with no lidar data points
    for i in range(num_of_interp):
        # print('Interpolating point %i of %i' % (i + 1, num_of_interp))
        # Find number of elements between these two points.
        # Linearly interpolate between two points
        # Move to net point

        if has_vals[1][i+1] == has_vals[1][i] + 1 or (has_vals[1][i+1] == 0 and has_vals[1][i] == ArrayInfo.len_lsp-1):
            continue    # No need to interpolate if points are next door to each other

        val_1 = temps_dist[has_vals[0][i], has_vals[1][i], ProcessInfo.DIST_IDX]
        val_2 = temps_dist[has_vals[0][i+1], has_vals[1][i+1], ProcessInfo.DIST_IDX]

        scan_dif = (has_vals[0][i+1] - has_vals[0][i])                  # Number of scans apart
        line_dif = has_vals[1][i+1] - has_vals[1][i]                    # Number of elements difference across the line
        num_el_dif = (scan_dif * ArrayInfo.len_lsp) + line_dif          # Number of elements between the 2 data points
        grad = (val_2 - val_1) / num_el_dif                             # Gradient for linear fit to data
        # print(has_vals[0][i], has_vals[0][i+1])
        # print(has_vals[1][i], has_vals[1][i+1])
        # print(scan_dif, line_dif, num_el_dif)

        # Calculate values
        elements = (np.arange(num_el_dif) * grad) + val_1
        elements = elements[1:]     # Don't use first element as it would replace the distance value we already have

        # If we have whole lines of empty data (scan_dif > 0) the assignment is slightly different
        if scan_dif > 0:

            line_start_idx = (has_vals[1][i] + 1) - ArrayInfo.len_lsp  # Starting index
            line_end_idx = has_vals[1][i + 1]
            # Assign values to incomplete scan lines
            temps_dist[has_vals[0][i], line_start_idx:, ProcessInfo.DIST_IDX] = elements[:abs(line_start_idx)]
            if line_end_idx != 0:
                # If index is zero we assign no values to this row, as there is already a value as the first element.
                temps_dist[has_vals[0][i+1], :line_end_idx, ProcessInfo.DIST_IDX] = elements[-line_end_idx:]
                elements_remain = elements[abs(line_start_idx):-line_end_idx]
            else:
                elements_remain = elements[abs(line_start_idx):]

            if scan_dif > 1:    # If at least one totally empty line (scan_dif > 1)
            # Iterate through each empty scan line and assign distances to entire line
                for scan in range(scan_dif - 1):
                    print(scan)
                    el_idx_start = scan * ArrayInfo.len_lsp
                    el_idx_end = (scan * ArrayInfo.len_lsp) + ArrayInfo.len_lsp
                    temps_dist[has_vals[0][i] + scan + 1, :, ProcessInfo.DIST_IDX] = elements_remain[el_idx_start:el_idx_end]
                    count += 1
        else:
            temps_dist[has_vals[0][i], (has_vals[1][i]+1):has_vals[1][i+1], ProcessInfo.DIST_IDX] = elements[:]

        # MAy need to apply correction to distance here because of the angle of the scan? Probably should use the proper
        # Data points as points of reference
        # OR could go back on another loop and do angle correction, as I won't be interpolating or messing with the angle dimension of the matrix in this loop
    print('Number of empty scans: %i' % np.sum(EMPTY_LID_FLAG))
    print('Number of empty rows in second processing: %i' % count)
    return temps_dist

directory = 'C:\\Users\\tw9616\\Documents\\PhD\\EE Placement\\Lidar\\RPLIDAR_A2M6\\VC2017 Test\\sdk\\output\\win32\\Release\\2018-02-08\\'
extension = '.mat'      # File extension for array we want to read in

files = [f for f in os.listdir(directory) if f.endswith(extension)]

temps_dist = np.zeros([ArrayInfo.NUM_SCANS, ArrayInfo.len_lsp, ProcessInfo.NUM_Z_DIM])  # Temperature/distance array (hold all information

lsp_proc = ProcessLSP()
data_array = lsp_proc.read_array(directory + files[-3])['arr']
print(data_array)
scan_speeds = data_array[:, ArrayInfo.speed_idx]
temps_dist[:, :, 0] = data_array[:, 0:ArrayInfo.len_lsp]
lidar = data_array[:, ArrayInfo.lid_idx_start:]
scan_num = np.arange(0, data_array.shape[0])

sorted_array = interpolate_data(lidar, temps_dist)

print('File prcessed: %s' % files[-3])

# Plot
f = plt.figure()
ax = f.add_subplot(111)
ax.plot(sorted_array[:, 500, ProcessInfo.TEMP_IDX])

f = plt.figure()
ax = f.add_subplot(111)
ax.plot(sorted_array[:, 500, ProcessInfo.DIST_IDX])
# for i in range(450, 550, 10):
#     ax.plot(sorted_array[:, i, ProcessInfo.DIST_IDX])

fig, ax1 = plt.subplots()
ax1.plot(sorted_array[:, 500, ProcessInfo.DIST_IDX], 'b-')
ax1.set_xlabel('Scan number')
ax1.set_ylabel('Distance [mm]', color='b')
ax1.tick_params('y', colors='b')

ax2 = ax1.twinx()
ax2.plot(sorted_array[:, 500, ProcessInfo.TEMP_IDX], 'r-')
ax2.set_ylabel(r'Temperature [$^o$C]', color='r')
ax2.tick_params('y', colors='r')

vector_distance = np.zeros((ArrayInfo.NUM_SCANS*ArrayInfo.len_lsp))  # Loop thorugh and put all distnces in here and then plot to look at the interpolation - is it wokring
for i in range(ArrayInfo.NUM_SCANS):
    idx = i * ArrayInfo.len_lsp
    vector_distance[idx:idx+ArrayInfo.len_lsp] = sorted_array[i, :, ProcessInfo.DIST_IDX]
# Plot
f = plt.figure()
ax = f.add_subplot(111)
ax.plot(vector_distance)
plt.show()


