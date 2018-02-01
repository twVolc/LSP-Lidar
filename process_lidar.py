# Overall aim should be to convert lidar data into point cloud data

import matplotlib.pyplot as plt
import numpy as np

# SHOULD CONVERT THIS HOLE THING TOT WOKRING WITH NUPY ARRAYS RATHER THAN LISTS, AS I QUITE OFTEN CONVERT TO ARRAYS THEN
# BACK TO LISTS. SOME METHODS WILL NEED A BIT OF CHANGING, AS APPENDING TO AN ARRAY IS A DIFFERENT METHOD I THINK

class LidarProcess:
    """Class to hold lidar data and process it
    Takes dictionary returned from read_lidar.py() containing fields:
    ->Distance
    ->Angle
    ->Quality"""
    def __init__(self, data_dict):
        self.data_dict = data_dict      # Dictionary holding scan data

        self.scan_time = None           # Holds start time of scan
        self.angle = None               # Holds angle data of scan
        self.angle_rad = None           # Holds angl in radians
        self.distance = None            # Holds distance data of scan
        self.quality = None             # Holds quality data of scan

        self._DATA_ERROR = 0            # Used as return if data is not all of same length
        self._DATA_GOOD = 1             # Used as return if data is all good

        self._DATA_EXTRACTED = False     # Boolean to determine whether data is extracted

    def extract_distance(self):
        """Extract distance to attribute"""
        self.distance = self.data_dict["distance"]

    def extract_angle(self):
        """Extract angle to attribute"""
        self.angle = self.data_dict["angle"]

    def extract_quality(self):
        """Extract quality to attribute"""
        self.quality = self.data_dict["quality"]

    def extract_all(self):
        """Extract all data for ease"""
        self.extract_distance()
        self.extract_angle()
        self.extract_quality()

    def __check_length__(self):
        """Check length of distance, angle and quality data.
        If data isn't the same length -> return 0"""
        if len(self.distance) == len(self.angle) and len(self.distance) == len(self.quality):
            return self._DATA_GOOD
        else:
            return self._DATA_ERROR

    def __check_data_extracted__(self):
        """Check that data has been extracted
        If it has -> _DATA_EXTACTED = True"""
        if self.distance is None or self.angle is None or self.quality is None:
            return
        else:
            self._DATA_EXTRACTED = True

    def check_data(self):
        """Performs a data check to make sure processing can occur"""
        self.__check_data_extracted__()
        if not self._DATA_EXTRACTED:
            print('Error!!! All data fields have not been correctly extracted. Data cannot be processed')
        if self.__check_length__() == self._DATA_ERROR:
            print('Error!!! Data must be same length for this request')
            return

    def get_length(self):
        """Returns number of data points in object"""
        self.check_data()
        return len(self.distance)

    def split_scans(self):
        """Split data into individual scans and returns a list of dictionaries containing each scan"""
        # Check data is in the correct format to be processed
        self.check_data()

        print('Separating scans...')

        # Create temporary variables for each parameter to ensure I don't do something to mess up the attributes
        _distance = self.distance
        _angle = self.angle
        _quality = self.quality

        # Initiate new dictionary
        dictionary_list = []        # List of dictionaries, each a separate scan
        dict_empty = {"distance": [], "angle": [], "quality": []}
        dictionary_list.append(dict_empty)
        dictionary_list[0]["distance"].append(_distance[0])
        dictionary_list[0]["angle"].append(_angle[0])
        dictionary_list[0]["quality"].append(_quality[0])

        # Iterate through lists, and assign to new dictionary when at start angle again
        dict_idx = 0
        for idx in range(1, len(_angle)):
            if _angle[idx] < _angle[idx-1]:  # If current angle is less than last angle we create new dictionary
                dictionary_list.append(dict_empty)  # Make new dictionary
                dict_idx += 1

            # Append current value at idx to the current dictionary
            dictionary_list[dict_idx]["distance"].append(_distance[idx])
            dictionary_list[dict_idx]["angle"].append(_angle[idx])
            dictionary_list[dict_idx]["quality"].append(_quality[idx])

        print('Data separated into %i scans' % (dict_idx+1))
        return dictionary_list

    def extract_between(self, start_angle, end_angle):
        """Extracts data between two angles and discards the rest
        Functino can loop around 360 such that if start_angle is greater than end_angle values will be extracted as if
        it involved all angles as you move from start_angle to end_angle on a compass"""
        _unchanged_angle = np.array(self.angle)     # Not edited but used in mask creation
        _distance = np.array(self.distance)         # Create np.array of list
        _angle = np.array(self.angle)
        _quality = np.array(self.quality)

        if start_angle < end_angle:
            _distance = _distance[np.logical_and(_unchanged_angle > start_angle, _unchanged_angle < end_angle)]
            _angle = _angle[np.logical_and(_unchanged_angle > start_angle, _unchanged_angle < end_angle)]
            _quality = _quality[np.logical_and(_unchanged_angle > start_angle, _unchanged_angle < end_angle)]
        elif start_angle > end_angle:
            _distance = _distance[np.logical_or(_unchanged_angle > start_angle, _unchanged_angle < end_angle)]
            _angle = _angle[np.logical_or(_unchanged_angle > start_angle, _unchanged_angle < end_angle)]
            _quality = _quality[np.logical_or(_unchanged_angle > start_angle, _unchanged_angle < end_angle)]
        else:
            print('Angles to extract between must be different.')
            return

        self.distance = _distance.tolist()
        self.angle = _angle.tolist()
        self.quality = _quality.tolist()

    def remove_bad_data(self):
        """Removes the data points with 0 quality
        Original data_dict remains unchanged, and can therefore be re-extracted if requested"""
        # Check data is in the correct format to be processed
        self.check_data()

        _distance = np.array(self.distance)
        _angle = np.array(self.angle)
        _quality = np.array(self.quality)

        _distance = _distance[_quality != 0]
        _angle = _angle[_quality != 0]
        _quality = _quality[_quality != 0]

        self.distance = _distance.tolist()
        self.angle = _angle.tolist()
        self.quality = _quality.tolist()

    def draw_plot(self):
        """Plot lidar data on polar axis"""
        # Check data is in the correct format to be processed
        self.check_data()
        self._convert_to_rad()

        # Draw plot
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='polar')
        self.scat_points = self.ax.scatter(self.angle_rad, self.distance, s=1)
        self.ax.set_theta_zero_location('N')
        self.ax.set_ylabel('Distance (mm)')
        plt.show()

    def _convert_to_rad(self):
        """Converts the angles to radians"""
        self.angle_rad = np.radians(np.array(self.angle)).tolist()