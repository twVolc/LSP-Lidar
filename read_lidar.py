import struct
import re


def read_lidar(filename):
    """Function to read binary lidar data into array"""

    # Extract header line and associated byte information for file
    with open(filename, 'rb') as f:
        header = f.readline()                       # Extract header line
        header_bytes = len(header)                  # Used for knowing how many bytes to skip for reading binary
        header = header.decode("utf-8")
        delimiter_list = [m.start() for m in re.finditer('_', header)]

        # EXTRACT DISTANCE BYTE SIZE AND SET FORMAT APPROPRIATELY
        distance_bytes = int(header[delimiter_list[0] + 1:delimiter_list[1] - 1])
        if distance_bytes == 2:
            distance_format = 'h'
        elif distance_bytes == 4:
            distance_format = 'f'
        elif distance_bytes == 8:
            distance_format = 'd'
        else:
            print('Unknown distance format. Please check data and retry')
            return

        # EXTRACT ANGLE BYTE SIZE AND SET FORMAT APPROPRIATELY
        angle_bytes = int(header[delimiter_list[2] + 1:delimiter_list[3] - 1])
        if angle_bytes == 4:
            angle_format = 'f'
        elif angle_bytes == 8:
            angle_format = 'd'
        else:
            print('Unknown angle format. Please check data and retry')
            return

        quality_bytes = int(header[delimiter_list[4] + 1:delimiter_list[5] - 1])
        if quality_bytes != 1:
            print('Expecting quality to be contained in 1 Byte. Please check data and retry')

    with open(filename, 'rb') as fb:
        fb.seek(header_bytes)                       # Ignore header
        distance = fb.read(distance_bytes)          # Extract distance
        angle = fb.read(angle_bytes)                # Extract angle
        quality = fb.read(quality_bytes)            # Extract quality

        count = 1
        while fb.read(1):       # Check we aren't at end of file
            fb.seek(-1, 1)      # Seek back the last byte so we are reading from the correct point
            distance += fb.read(distance_bytes)
            angle += fb.read(angle_bytes)
            quality += fb.read(quality_bytes)

            count += 1

        count_str = str(count)

        distances = struct.unpack(count_str+distance_format, distance)  # Unpack bytes into floats
        angles = struct.unpack(count_str+angle_format, angle)  # Unpack bytes into floats
        qualities = struct.unpack(count_str+'B', quality)  # Unpack bytes into floats

        return {"distance": distances, "angle": angles, "quality": qualities}

def extract_scans(data_dict):
    """Function takes lidar data of multiple scans and returns list of dictionaries of individual scans"""
    # HAve this implemented in process lidar  not sure if I want it here or there.
    pass

if __name__ == '__main__':
    filename = 'C:\\Users\\tw9616\\Documents\\PhD\\EE Placement\\Lidar\\RPLIDAR_A2M6\\VC2017 Test\\sdk\\output\\win32\\Release\\2018-01-16\\2018-01-16_T125704.dat'
    values = read_lidar(filename)
