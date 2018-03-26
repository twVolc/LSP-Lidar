import cv2
import numpy as np
from OpticalFlow import OptiFlow


class VideoReader:
    def __init__(self, vid_path):
        self.vid_path = vid_path

        # Create capture object
        self.vid_obj = cv2.VideoCapture(vid_path)

        self.frame_step = 10    # Number of frames to step in one read

        self.current_frame = None
        self.next_frame = None
        self.end_of_file = False


    def read_frame(self):
        """Read a frame_setts of the image"""
        if isinstance(self.next_frame, np.ndarray):  # Do this check as for first from we can't copy None
            self.current_frame = np.copy(self.next_frame)

        for i in range(self.frame_step):
            ret, frame = self.vid_obj.read()
            if not ret:
                self.end_of_file = True
                print('File Ended!!!')
                self.vid_obj.release()
                cv2.destroyAllWindows()
                return

        # Take just one channel of the frame_setts
        self.next_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)


if __name__ == '__main__':
    vid_file = 'C:\\Users\\tw9616\\Documents\\PhD\\EE Placement\\Therm_Lidar Python\Data\\2018-03-21\\2017-08-22_142344_u374982.h264'
    my_vid = VideoReader(vid_file)
    opti_flow = OptiFlow()

    while not my_vid.end_of_file:
        my_vid.read_frame()
        print('Got frame...')
        if isinstance(my_vid.current_frame, np.ndarray):
            opti_flow.compute_flow(my_vid.current_frame, my_vid.next_frame)




