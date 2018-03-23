# SIMPLE SCRIPT TO CAPTURE VIDEO AND SAVE IT EVERY 'record_time' SECONDS

import picamera
import datetime
import os

extension = '.h264'         # Video file extension
record_time = 10            # Length (in seconds) of each video before it is split
main_dir = './Pi_Videos/' + datetime.datetime.now().strftime('%Y-%m-%d') + '/'
if not os.path.exists(main_dir):
    os.makedirs(main_dir)

with picamera.PiCamera() as camera:
    camera.resolution = (640, 480)
    camera.framerate = 90
    filename = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S_u%f')
    camera.start_recording(main_dir + filename + extension)
    camera.wait_recording(record_time)
    while 1:
        filename = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S_u%f')
        camera.split_recording(main_dir + filename + extension)
        camera.wait_recording(record_time)
    camera.stop_recording()
