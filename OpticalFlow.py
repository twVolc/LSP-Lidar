import cv2
import scipy.misc
import numpy as np

class OptiFlow:
    """NOTE: When plotting velocities on a resampled grid, the vectors will appear too large
    (point further than in fact the pxels move)
    This is not an error, this is because the vectors are now plotted on the resampled grid,
    where each pixel is in effect larger than the pixels of the image they are plotted on top of. The vectors would need
    to be scaled by the ratio factor if they are to accurately represent flow paths."""
    def __init__(self):

        self.pyr_scale = 0.5
        self.levels = 4
        self.winsize = 40
        self.iterations = 5
        self.poly_n = 5
        self.poly_sigma = 1.1
        self.resample_size = 100

        self.velocities = None
        self.x_shifts = None
        self.y_shifts = None
        self.extent = None

    def compute_flow(self, current_image, next_image):
        """Generate flow vectors from Frneback optical flow algorithm"""
        self.velocities = cv2.calcOpticalFlowFarneback(current_image, next_image, None,
                                                       self.pyr_scale,
                                                       self.levels,
                                                       self.winsize,
                                                       self.iterations,
                                                       self.poly_n,
                                                       self.poly_sigma,
                                                       flags=cv2.OPTFLOW_FARNEBACK_GAUSSIAN)
        self.x_shifts, self.y_shifts, self.extent = self.resample_velocities(self.velocities, int(self.resample_size))
        #print('Optical flow computed!')

        # self.__update_optical_flow__(current_image)

    def resample_velocities(self, velocities, yn):
        """
        Downsamples the velocities array (an MxNx2 array) such that N=yn and M is
        such that the downsampled array has the same aspect ratio as the original.

        For efficiency, nearest neighbour interpolation is used.
        """
        xvel = velocities[..., 0]
        yvel = velocities[..., 1]

        if yn > xvel.shape[1]:
            raise ValueError("Cannot resample velocities to higher resolution than the original.")

        # Calculate scalar to reduce shifts by in order to give accurate vectors
        self.vel_scalar = yn / xvel.shape[1]

        x_size = int(round((float(yn) / xvel.shape[1]) * xvel.shape[0], 0))

        x_shifts = scipy.misc.imresize(xvel, (x_size, yn), 'nearest', 'F')
        y_shifts = scipy.misc.imresize(yvel, (x_size, yn), 'nearest', 'F')

        extent = (0.0, float(yn - 1), float(x_size - 1), 0.0)

        return x_shifts, y_shifts, extent

    def save_shifts(self, filename):
        """Save shifts as ASCII"""
        with open(filename, 'w') as f:
            f.write('x_shifts\ty_shifts\r\n')
            for i in range(len(self.x_shifts)):
                f.write('{}\t{}\r\n'.format(self.x_shifts[i], self.y_shifts[i]))