from LSP_control import ProcessLSP
from server import Instruments
import matplotlib.pyplot as plt
import os
from data_handler import ArrayInfo
import numpy as np
from scipy import interpolate
import sys


class ProcessInfo:
    """Contains properties used in post-processing data
    -> User may need to change these properties"""
    LIDAR_LSP_DIST = 0.11       # Distance between Lidar and LSP acquisition positions (metres)
    INSTRUMENT_SPEED = 0.05     # Speed of movement (m/s)
    INSTRUMENT_DIRECTION = 1    # Scan direction (LSP first=1, Lidar first=-1)
    SHIFT_SCANS = True          # Boolean for whether or not we apply the movement shift (True is generally required)

    # Define array to hold all of the data
    NUM_Z_DIM = 3           # Number of z-dimensions (Currently: Temperature/Distance/Angle)
    TEMP_IDX = 0            # Index for z dimension where temperature information is stored
    DIST_IDX = 1            # Index for z dimension where distance information is stored
    ANGLE_IDX = 2           # Index for z dimension where angle information is stored

    LIDAR_PADDING = 0       # Padding of lidar distance data (sets values around a measurement to the same value). Used because LSP angular resolution is much higher than lidar

    # Generate 1D array holding angles of LSP data points
    _range_lsp_angle = 80                   # Range of angles measured by LSP
    LSP_ANGLES = np.linspace(0, _range_lsp_angle, ArrayInfo.len_lsp) - (_range_lsp_angle / 2)
    LSP_MIN_ANGLE = np.min(LSP_ANGLES) - 0.5    # Angles outside of this range are discarded
    LSP_MAX_ANGLE = np.max(LSP_ANGLES) + 0.5    # Angles outside of this range are discarded
    LIDAR_ANGLE_OFFSET = -90                # Shift applied to lidar angles to match with LSP

    # Define method of interpolation for lidar measurements
    # Time interpolation takes data from lidar and spreads it evenly across contemporaneous LSP scan, regardless of scan angle
    # Angle interpolation matches angles on lidar to angles on LSP (Angle is recommended - Time may be a stupid idea)
    TIME_INTERP = False         # User can change this value (True/False)
    if not TIME_INTERP:
        ANGLE_INTERP = True
    else:
        ANGLE_INTERP = False
    INTERP_METHOD = 'cubic'     # Method of interpolation for 2d_interp()


def process_data(lidar_data, temps_dist, scan_speeds):
    """Main processing function
    -> Positions lidar data in main array
    -> Interpolates lidar data such that every temperature point has an associated distance
    -> Returns processed array"""
    movement_speed = ProcessInfo.INSTRUMENT_SPEED       # Will want to change this assignement when we stream speed
    corr_scan = None    # Just intialising variable which needs to exists in first main loop - correct scan index

    EMPTY_LID_FLAG = np.zeros([ArrayInfo.NUM_SCANS])    # Array holding flags if lidar data is empty for that scan
    lid_scan_size = lidar_data.shape[1]                 # Number of elements avaailable for lidar data per LSP scan
    distance_idxs = np.arange(Instruments.LIDAR_DIST_IDX, lid_scan_size, Instruments.NUM_LIDAR_PTS)     # Indices for extraction of all distance data points per scan line
    angle_idxs = np.arange(Instruments.LIDAR_ANGLE_IDX, lid_scan_size, Instruments.NUM_LIDAR_PTS)       # As above
    quality_idxs = np.arange(Instruments.LIDAR_QUAL_IDX, lid_scan_size, Instruments.NUM_LIDAR_PTS)      # As above

    pad = ProcessInfo.LIDAR_PADDING     # Set padding for lidar data
    # -----------------------------------------------------------------------------------------------------------------
    # First iterations - find where lidar data is and put it into array with indices corresponding to a temperature
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
            # Calculate what scan line the lidar data needs to be placed on - shift dependent on movement/scan speed etc
            # Only done if SHIFT_SCANS flag is True, otherwise process data without shifting scans
            if ProcessInfo.SHIFT_SCANS:
                prev_scan = corr_scan
                corr_scan = scan_shift(scan_speeds, scan, movement_speed)
                if corr_scan is None:
                    continue        # If function returns None - no match for LSP line, we continue
            else:
                corr_scan = scan    # Just use scan index
                prev_scan = -1      # Set as dummy so we don't edit corr scan later on

            # PLACING LIDAR DATA IN ARRAY > DEPENDENT ON REQUESTED METHOD
            if ProcessInfo.TIME_INTERP:
                if corr_scan == prev_scan:
                    corr_scan += 1          # Correct the scan to next line if we have already used line

                # Find how to spread lidar data points across scan
                spread_dat = int(np.floor(ArrayInfo.len_lsp / (num_dat + 1)))

                for i in range(num_dat):
                    if (angles[i] + 1) > ProcessInfo.LSP_MAX_ANGLE or (angles[i] + 1) < ProcessInfo.LSP_MIN_ANGLE:
                        EMPTY_LID_FLAG[scan] = 1  # Flag that we have no data for this scan
                        continue  # Ignore measurements outside of the FOV of the LSP
                    idx = (i + 1) * spread_dat                                  # Index for placing value
                    temps_dist[corr_scan, idx, ProcessInfo.DIST_IDX] = distances[i]  # Assign distance value
                    temps_dist[corr_scan, idx, ProcessInfo.ANGLE_IDX] = angles[i]    # Assign angle value

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
                    if idx < pad:
                        temps_dist[corr_scan, 0:(idx+pad+1), ProcessInfo.DIST_IDX] = distances[i]    # Assign distance value
                        temps_dist[corr_scan, 0:(idx+pad+1), ProcessInfo.ANGLE_IDX] = angles[i]      # Assign angle value
                    else:
                        temps_dist[corr_scan, (idx-pad):(idx+pad+1), ProcessInfo.DIST_IDX] = distances[i]  # Assign distance value
                        temps_dist[corr_scan, (idx-pad):(idx+pad+1), ProcessInfo.ANGLE_IDX] = angles[i]    # Assign angle value

            else:
                print('Error! Processing method [in <class>ProcessInfo] incorrectly defined.')
                sys.exit()


    # Perform interpolation of data
    raw_lid = np.copy(temps_dist[:, :, ProcessInfo.DIST_IDX])   # Extract raw distance data so it can be returned separately to interpolated array
    temps_dist[:, :, ProcessInfo.DIST_IDX] = interp_2D(temps_dist[:, :, ProcessInfo.DIST_IDX])



    return temps_dist, raw_lid


def scan_shift(scan_speeds, idx, movement_speed):
    """Calculate the shift in scan line data needed to correct for instrument offset/movement speed"""
    # Need to think about when scan speed == 0, when we don't have a line of data. I think I should just remove these lines from the array, and shift everything up.
    # This divide by zero is what is ruining the data
    incr = ProcessInfo.INSTRUMENT_DIRECTION # Get increment from class (either +1 or -1 depending on instrument orientation)

    time_taken = ProcessInfo.LIDAR_LSP_DIST / movement_speed

    num_scans = len(scan_speeds)
    scan_time = 0
    while scan_time < time_taken:
        # Return if we have reached the first point of data and still haven't got to the time required
        if idx < 0 or idx >= num_scans:
            print('Lidar offset extends beyond the bounds of LSP data')
            return None
        elif scan_speeds[idx] == 0:
            print('Scan speed=0, either all blank LSP lines have not been removed, or we have reached the end of the data')
            return None

        # Loop backwards through scan speeds, summing the time of each line until we reach the time taken
        scan_time += (1/scan_speeds[idx])

        idx = idx - incr

    # Determine whether this final scan, or the previous scan were closest to the time_taken
    prev_scan_time = scan_time - (1/scan_speeds[idx+incr])  # Subtract final scan time to get previous cumulative time
    difference = [abs(time_taken-scan_time), abs(time_taken-prev_scan_time)]
    closest_scan = np.argmin(difference)

    if closest_scan == 1:
        idx = idx + (2*incr)        # Correct index if we want to use previous scan as final answer
    elif closest_scan == 0:
        idx = idx + incr        # Return back to final index if we want to use that as final answer
    else:
        print('Error determining scan position')
        return None
    return idx

def interp_2D(data_grid):
    """Perform 2D interpolation on data"""
    print('Interpolating data...')
    meth = ProcessInfo.INTERP_METHOD    # Get method for interpolating

    xy_grid = np.nonzero(data_grid)
    z_grid = data_grid[xy_grid]
    grid_x, grid_y = np.mgrid[0:1000:1000j, 0:1000:1000j]
    interp_grid = interpolate.griddata(xy_grid, z_grid, (grid_x, grid_y), method=meth)

    return interp_grid

def remove_empty_scans(data_array):
    """Iterates through scan rows and removes empty scans where thermal data hasn't been recorded
    -> Just shifts everything up a row"""
    # Think about what to do with lidar data, as shifting that up a row might cause issues if there is already data in row above
    # But leaving the data where it is may mean things get out of sync?
    for scan in range(ArrayInfo.NUM_SCANS):
        if data_array[scan, ArrayInfo.speed_idx] == 0:  # Use scan speed as identifier of no data
            # Check if there is lidar data in the scan
            if np.max(data_array[scan, ArrayInfo.speed_idx]) == 0:
                # If no data is in scan shift everything up
                data_array[scan:-1, :] = data_array[scan+1:, :]
            else:
                scan_new = scan - 1
                while np.max(data_array[scan_new, ArrayInfo.lid_idx_start:]) != 0:
                    scan_new -= 1

                # Remove empty line by shifting all data points upwards for temp and scan speed only
                data_array[scan:-1, 0:ArrayInfo.lid_idx_start] = data_array[scan+1:, 0:ArrayInfo.lid_idx_start]

                # Then shift lidar info up separately, moving all above points too where necessary (so we don't overwrite lines)
                data_array[scan_new:-1, ArrayInfo.lid_idx_start:] = data_array[scan_new+1:, ArrayInfo.lid_idx_start:]

            # Finally, whatever the above shifting process, we append zeros to the final line
            data_array[-1, :] = 0
            pass

    # Return modified data array
    return data_array

directory = 'C:\\Users\\tw9616\\Documents\\PhD\\EE Placement\\Lidar\\RPLIDAR_A2M6\\VC2017 Test\\sdk\\output\\win32\\Release\\2018-02-08\\'
extension = '.mat'      # File extension for array we want to read in

# List files
files = [f for f in os.listdir(directory) if f.endswith(extension)]

# Intiate main array for data holding
temps_dist = np.zeros([ArrayInfo.NUM_SCANS, ArrayInfo.len_lsp, ProcessInfo.NUM_Z_DIM])  # Temperature/distance array (hold all information

# Read in data
lsp_proc = ProcessLSP()
data_array = lsp_proc.read_array(directory + files[-3])['arr']
data_array = remove_empty_scans(data_array)

# Extract scan speeds, temperature data and then lidar data
scan_speeds = data_array[:, ArrayInfo.speed_idx]
temps_dist[:, :, ProcessInfo.TEMP_IDX] = data_array[:, 0:ArrayInfo.len_lsp]
lidar = data_array[:, ArrayInfo.lid_idx_start:]
scan_num = np.arange(0, data_array.shape[0])

# Perform main processing, positioning lidar data and interpolating it to fill up data points
sorted_array, raw_lid = process_data(lidar, temps_dist, scan_speeds)

print('File processed: %s' % files[-3])

# Plot
f = plt.figure()
ax = f.add_subplot(111)
ax.plot(sorted_array[:, 500, ProcessInfo.TEMP_IDX])

f = plt.figure()
ax = f.add_subplot(111)
ax.plot(sorted_array[:, 500, ProcessInfo.DIST_IDX])
# for i in range(450, 550, 10):
#     ax.plot(sorted_array[:, i, ProcessInfo.DIST_IDX])

# Distance + temperature plots
for i in range(0, 1000, 100):
    fig, ax1 = plt.subplots()
    ax1.plot(sorted_array[:, i, ProcessInfo.DIST_IDX], 'b-')
    ax1.set_xlabel('Scan number')
    ax1.set_ylabel('Distance [mm]', color='b')
    ax1.tick_params('y', colors='b')

    ax2 = ax1.twinx()
    ax2.plot(sorted_array[:, i, ProcessInfo.TEMP_IDX], 'r-')
    ax2.set_ylabel(r'Temperature [$^o$C]', color='r')
    ax2.tick_params('y', colors='r')


# -------------------------------------------------------------------------------------------------
# Colourmap images of temperature and distance
# Raw lidar plot
f, ax = plt.subplots()
img = ax.imshow(raw_lid, cmap='nipy_spectral')
cbar = f.colorbar(img)
cbar.set_label('Distance [mm]')

# Interpolated lidar plot
f, ax = plt.subplots()
img = ax.imshow(temps_dist[:, :, ProcessInfo.DIST_IDX], cmap='nipy_spectral')
cbar = f.colorbar(img)
cbar.set_label('Distance [mm]')

# Temperature plot
f, ax = plt.subplots()
img = ax.imshow(sorted_array[:, :, ProcessInfo.TEMP_IDX], cmap='nipy_spectral')
cbar = f.colorbar(img)
cbar.set_label(r'Temperature [$^o$C]')
# -------------------------------------------------------------------------------------------------

plt.show()