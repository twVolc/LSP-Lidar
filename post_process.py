# MAIN FILE FOR POST PROCESSING OF DATA

from LSP_control import ProcessLSP
from server import Instruments
import matplotlib.pyplot as plt
import os
from data_handler import ArrayInfo
from GUI_subs import MessagesGUI
import numpy as np
from scipy import interpolate
import sys
import h5py
from laspy import file as lasfile
from laspy import header as lashead


class ProcessInfo(ArrayInfo):
    """Contains properties used in post-processing data
    -> User may need to change these properties"""
    LIDAR_LSP_DIST_HOR = 0.0    # Horizontal Distance between Lidar and LSP acquisition positions (mm)
    LIDAR_LSP_DIST_VERT = 11    # Vertical Distance between Lidar and LSP acquisition positions (mm)
    INSTRUMENT_SPEED = 0.05     # Speed of movement (m/s)
    INSTRUMENT_DIRECTION = 1    # Scan direction (LSP first=1, Lidar first=-1)
    SHIFT_SCANS = False         # Boolean for whether or not we apply the movement shift (True is generally required) In new system the  shift isn't necessary as the scans are alligned
    ADJ_ANGLE = True            # Boolean for whether we should adjust the Lidar angle (and distance) for offset between LSP and Lidar

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
    LIDAR_ANGLE_OFFSET = 0                # Shift applied to lidar angles to match with LSP

    # Define method of interpolation for lidar measurements
    # Time interpolation takes data from lidar and spreads it evenly across contemporaneous LSP scan, regardless of scan angle
    # Angle interpolation matches angles on lidar to angles on LSP (Angle is recommended - Time may be a stupid idea)
    TIME_INTERP = False         # User can change this value (True/False)
    if not TIME_INTERP:
        ANGLE_INTERP = True
    else:
        ANGLE_INTERP = False
    INTERP_METHOD = 'cubic'     # Method of interpolation for 2d_interp()


class ErrorDist:
    """Class for distance error calculations"""
    min_error = 0.0005        # If there is a minimum error for every value below a spcified distance
    min_error_dist = 1.5   # The distance for which the minimum error is always quoted
    error_prop = 0.01       # Proportional error for error outside the minimum error range

    def calc_error(self, data):
        """Calculate errors for each element in a dataset"""
        errors = np.zeros(data.shape)

        # Values below minimum lidar distance are ascribed the minimum error
        errors[data <= self.min_error_dist] = self.min_error

        # Values above minimum have erros calculated by proportion of their value
        errors[data > self.min_error_dist] = data[data > self.min_error_dist] * self.error_prop
        return errors


class DataProcessor:
    """Class to handle and hold all of the data for the GUI, and data processing
    -> Eventually this should incoorporate all functions currently help in this file"""
    def __init__(self, q_dat=None, mess_inst=None):
        self._num_pts = ProcessInfo.len_lsp     # Number of data points in LSP scan
        self.num_scans = 1000       # Number of scan lines in data array - may want to define this in a different way, rather than explicitly here, so that it can be easily varied (i.e. use numpy.shape on data array)
        self.temp_idx = 0
        self.x_idx = 3              # Index for x coordinates of array
        self.y_idx = 4              # Index for y coordinates of array
        self.z_idx = 1              # Index for distance coordinate of array
        self._len_z = 5             # Length of array z dimension (Temperature, Distance (z), angle, x, y) - in time angle can be directly translated to y, but for now we leave it all in there

        self.q_dat = q_dat          # Queue for putting data in
        self.mess_inst = mess_inst  # Instance of MessagesGUI() for sending messages if necessary

        self.data_array = None
        self.raw_lidar = None
        self.xyz_array = np.zeros([self._num_pts, self.num_scans, self._len_z])
        self.flat_array = None

    def __check_array__(self):
        """Housekeeping method, to check that we have data before we attempt to process it"""
        if self.data_array is None:
            mess = 'No data array is present, please load before attempting to create XYZ array.'
            if isinstance(self.mess_inst, MessagesGUI):
                self.mess_inst.message(mess)
            else:
                print(mess)
            return False
        else:
            return True

    def __check_flat_array__(self):
        """Check if we have a flattened array"""
        if self.flat_array is not None:
            return True
        else:
            return False

    def flatten_array(self):
        """Flatten xyz array to enable plotting"""
        numel = self.xyz_array[:, :, 0].size                # Number of elements in dataset
        self.flat_array = np.zeros([self._len_z, numel])    # Create array to hold flattened array

        # Loop through each dimension (dataset) and flatten it into new array
        for dim in range(self._len_z):
            self.flat_array[dim, :] = np.ravel(self.xyz_array[:, :, dim])

    def get_x(self):
        if self.__check_flat_array__():
            return self.flat_array[self.x_idx, :]
        else:
            return None
    def get_y(self):
        if self.__check_flat_array__():
            return self.flat_array[self.y_idx, :]
        else:
            return None
    def get_z(self):
        if self.__check_flat_array__():
            return self.flat_array[self.z_idx, :]
        else:
            return None
    def get_temp(self):
        if self.__check_flat_array__():
            return self.flat_array[self.temp_idx, :]
        else:
            return None

    def calc_error_dist(self):
        """Calculates the error of the dstance measurements based on RPlidar's error specifications"""
        pass

    def save_hdf5(self, filename):
        """Saves array in HDF5 format - universal format which can be read in C++ too"""
        filename += '.h5'
        try:
            hf = h5py.File(filename, 'w')
            hf.create_dataset('Array', data=self.flat_array)
            hf.close()
        except TypeError as err:
           self.mess_inst.message('TypeError [{}] when attempting to save HDF5'.format(err))

    def save_ASCII(self, filename):
        """Save xyz coordinates and temperature as ASCII file in columns"""
        pass

    def create_xyz_basic(self):
        """Generate a basic xyz array with no hold on speed, purely arbitrary distances"""
        if not self.__check_array__():
            return

        self.xyz_array[:, :, :3] = self.data_array

        # Iterate through each scan and assign it and arbitrary x coordinate (1st scan is 0, 2nd is 1 etc)
        for x in range(self.num_scans):
            self.xyz_array[:, x, self.x_idx] = x

        # Iterate through each scan angle and give an arbitrary y coordinate
        for y in range(self._num_pts):
            # Reverse indices so that we start with bottom of array
            # > np index starts top left as 0,0 but we want to set 0,0 as bottom left so that y increase up the rows
            idx = self._num_pts - (y + 1)
            self.xyz_array[idx, :, self.y_idx] = y

        if isinstance(self.mess_inst, MessagesGUI):
            self.mess_inst.message('XYZ array created successfully!!!')
        else:
            print('XYZ array created successfully!!!')

        self.flatten_array()

    def generate_LAS(self, filename):
        """Create a .las file, or object to be saved"""
        try:
            filename = filename.split('.')[0] + '.LAS'
            headerobj = self.__make_header__()
            fileobj = lasfile.File(filename, mode='w', header=headerobj)
            fileobj.X = self.flat_array[self.x_idx, :]
            fileobj.Y = self.flat_array[self.y_idx, :]
            fileobj.Z = self.flat_array[self.z_idx, :]
            fileobj.Intensity = self.flat_array[self.temp_idx, :]
            fileobj.close()
        except AttributeError as err:
            self.mess_inst.message('AttributeError [{}] when attempting to generate .LAS file'.format(err))
        except TypeError as err:
            self.mess_inst.message('TypeError [{}] when attempting to generate .LAS file'.format(err))

    def __make_header__(self):
        """Create header object for .LAS format and return it"""
        header = lashead.Header(point_format=0)

        return header

def process_data_alligned(lidar_data, temps_dist, scan_speeds, info=ProcessInfo(), q_dat=None):
    """Similar to process_data() but for new setup where lidar and LSP scan planes are alligned
    -> Removes any blank lines of LSP data
    -> Positions lidar data in main array, scaling distance to temperature distance if necessary (small offset between LSP and Lidar)
    -> Interpolates lidar data
    -> returns main array"""

def process_data(lidar_data, temps_dist, scan_speeds, info=ProcessInfo(), q_dat=None):
    """Main processing function
    -> Positions lidar data in main array
    -> Interpolates lidar data such that every temperature point has an associated distance
    -> Returns processed array"""
    movement_speed = info.INSTRUMENT_SPEED       # Will want to change this assignement when we stream speed
    corr_scan = None    # Just intialising variable which needs to exists in first main loop - correct scan index

    EMPTY_LID_FLAG = np.zeros([info.NUM_SCANS])    # Array holding flags if lidar data is empty for that scan
    lid_scan_size = lidar_data.shape[1]                 # Number of elements avaailable for lidar data per LSP scan
    distance_idxs = np.arange(Instruments.LIDAR_DIST_IDX, lid_scan_size, Instruments.NUM_LIDAR_PTS)     # Indices for extraction of all distance data points per scan line
    angle_idxs = np.arange(Instruments.LIDAR_ANGLE_IDX, lid_scan_size, Instruments.NUM_LIDAR_PTS)       # As above
    quality_idxs = np.arange(Instruments.LIDAR_QUAL_IDX, lid_scan_size, Instruments.NUM_LIDAR_PTS)      # As above

    pad = info.LIDAR_PADDING     # Set padding for lidar data
    # -----------------------------------------------------------------------------------------------------------------
    # First iterations - find where lidar data is and put it into array with indices corresponding to a temperature
    for scan in range(info.NUM_SCANS):
        print('Processing scan %i of %i' % (scan + 1, info.NUM_SCANS))
        # Iterate through the scans assigning a distance and angle to each temperature measurement
        # Need to interpolate across a scan where necessary by finding the number of lidar points for that scan line
        # Also need to interpolate between scans where no lidar data is found
        distances = lidar_data[scan, distance_idxs]
        angles = lidar_data[scan, angle_idxs] + info.LIDAR_ANGLE_OFFSET  # Apply offset to angles to match LSP
        angles[angles >= 320] = (angles[angles >= 320] - 360)     # Possibly the adjustment needed here
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
            if info.SHIFT_SCANS:
                prev_scan = corr_scan
                corr_scan = scan_shift(scan_speeds, scan, movement_speed, info=info)
                if corr_scan is None:
                    continue        # If function returns None - no match for LSP line, we continue
            else:
                corr_scan = scan    # Just use scan index
                prev_scan = -1      # Set as dummy so we don't edit corr scan later on

            # --------------------------------------------------------------------------------------------------------
            # PLACING LIDAR DATA IN ARRAY > DEPENDENT ON REQUESTED METHOD
            # -------------------------------------------------------------------------------------------------------
            if info.TIME_INTERP:
                # NOT RECOMMENDED!!!!
                if corr_scan == prev_scan:
                    corr_scan += 1          # Correct the scan to next line if we have already used line

                # Find how to spread lidar data points across scan
                spread_dat = int(np.floor(info.len_lsp / (num_dat + 1)))

                for i in range(num_dat):
                    if (angles[i] + 1) > info.LSP_MAX_ANGLE or (angles[i] + 1) < info.LSP_MIN_ANGLE:
                        EMPTY_LID_FLAG[scan] = 1  # Flag that we have no data for this scan
                        continue  # Ignore measurements outside of the FOV of the LSP
                    idx = (i + 1) * spread_dat                                  # Index for placing value
                    temps_dist[corr_scan, idx, info.DIST_IDX] = distances[i]  # Assign distance value
                    temps_dist[corr_scan, idx, info.ANGLE_IDX] = angles[i]    # Assign angle value
            # -------------------------------------------------------------------------------------------------------

            elif info.ANGLE_INTERP:
                # Loop through angles and assign data to the specific angle it corresponds to in the LSP scan
                for i in range(num_dat):
                    if (angles[i] + 1) > info.LSP_MAX_ANGLE or (angles[i] + 1) < info.LSP_MIN_ANGLE:
                        EMPTY_LID_FLAG[scan] = 1  # Flag that we have no data for this scan
                        continue    # Ignore measurements outside of the FOV of the LSP

                    if info.ADJ_ANGLE:
                        return_val = find_lsp_angle(angles[i], distances[i], info)
                        angle = return_val[0]
                        distance = return_val[1]
                    else:
                        angle = angles[i]
                        distance = distances[i]

                    idx = np.argmin(abs(info.LSP_ANGLES - angle))
                    # print(idx)

                    # Assigning distance value with padding (5 temperature points are assigned the same distance)
                    # Done because the angular resolution of the LSP far exceeds that of the lidar
                    # Values at edge of FOV are padded differently (don't need to have specific assignments for upper
                    # indices of array because over assignment of indices just gets ignored in python
                    if idx < pad:
                        temps_dist[corr_scan, 0:(idx+pad+1), info.DIST_IDX] = distance    # Assign distance value
                        temps_dist[corr_scan, 0:(idx+pad+1), info.ANGLE_IDX] = angle      # Assign angle value
                    else:
                        temps_dist[corr_scan, (idx-pad):(idx+pad+1), info.DIST_IDX] = distance  # Assign distance value
                        temps_dist[corr_scan, (idx-pad):(idx+pad+1), info.ANGLE_IDX] = angle    # Assign angle value
            # ----------------------------------------------------------------------------------------------------------
            else:
                print('Error! Processing method [in <class>ProcessInfo] incorrectly defined.')
                sys.exit()
            # ----------------------------------------------------------------------------------------------------------

    # Perform interpolation of data
    raw_lid = np.copy(temps_dist[:, :, info.DIST_IDX])   # Extract raw distance data so it can be returned separately to interpolated array
    temps_dist[:, :, info.DIST_IDX] = interp_2D(temps_dist[:, :, info.DIST_IDX])

    # USe queue to return data if this function is a thread - don't think this is necessary in the end
    if q_dat is not None:
        q_dat.put(temps_dist)
        q_dat.put(raw_lid)

    return temps_dist, raw_lid


def find_lsp_angle(angle, distance, info=ProcessInfo()):
    """Finds associated LSP angle which will coincide with a lidar data point for angle and distance"""

    # Calculate angle used for trig calculations
    angle_corr = angle + 90

    # Find distance between LSP and object (cosine rule)
    therm_dist = np.sqrt(distance**2 + info.LIDAR_LSP_DIST_VERT**2 -
                         (2 * distance * info.LIDAR_LSP_DIST_VERT * np.cos(np.deg2rad(angle_corr))))

    # Find thermal angle with cosine rule
    therm_angle = np.rad2deg(np.arccos((therm_dist**2 + info.LIDAR_LSP_DIST_VERT**2 - distance**2)
                                 / (2*therm_dist*info.LIDAR_LSP_DIST_VERT)))

    # If we have an obtuse angle it needs to be converted from the -ve (np.arcsin/cos returns between -pi/2 and pi/2)
    if therm_angle < 0:
        therm_angle += 180

    # Convert therm_angle to LSP angle (LSP angles defined as between -x and x so that 0 is the horizontal scan)
    # lsp_angle = (therm_angle - 90) * -1
    lsp_angle = 90 - therm_angle

    print('Therm angle: {}\tLSP angle: {}\tLidar angle: {}'.format(therm_angle, lsp_angle, angle))
    return [lsp_angle, therm_dist]


    # Need to convert back to proper thermal angle eventually (between -40 and 40)


def scan_shift(scan_speeds, idx, movement_speed, info=ProcessInfo()):
    """Calculate the shift in scan line data needed to correct for instrument offset/movement speed"""
    # Need to think about when scan speed == 0, when we don't have a line of data. I think I should just remove these lines from the array, and shift everything up.
    # This divide by zero is what is ruining the data
    incr = info.INSTRUMENT_DIRECTION # Get increment from class (either +1 or -1 depending on instrument orientation)

    time_taken = info.LIDAR_LSP_DIST_HOR / movement_speed

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

def interp_2D(data_grid, info=ProcessInfo()):
    """Perform 2D interpolation on data"""
    print('Interpolating data...')
    meth = info.INTERP_METHOD    # Get method for interpolating

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




if __name__ == '__main__':
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