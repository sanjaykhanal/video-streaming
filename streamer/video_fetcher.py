"""
Video Fetcher
"""
from time import sleep
import logging
from threading import Thread
import cv2

from custom_queue import Queue



def rotate_image(image, rotation):
    im_shape = image.shape
    rotation_matrix = cv2.getRotationMatrix2D(
        (int(im_shape[1] / 2), int(im_shape[0] / 2)), rotation, 1)
    return cv2.warpAffine(image, rotation_matrix, (im_shape[1], im_shape[0]))


class VideoFetcher:

    def __init__(self, src=0, local=False, cam_id=None, rotation=0, roi=None, 
                 loop=True, q=True, q_size=30, address="localhost"):
        self.src = src
        self.q = q
        self.local = local
        self.cam_id = cam_id
        self.loop = loop
        self.rotation = rotation
        self.roi = roi
        self.port = None
        self.address = address
        self.frame = None
        self.frames = Queue(q_size)
        self.is_camera_live = False
        self.last_event = ''


    def __connect(self):
        self.stream = cv2.VideoCapture(self.src)

        self.grabbed, self.frame = self.stream.read()
        if not self.grabbed:
            self.stream.release()
            sleep(1)
            self.stream = cv2.VideoCapture(self.src)
            # self.stream = cv2.VideoCapture("rtspsrc location=rtsp://192.168.1.200:554/Streaming/channels/101 user-id=admin user-pw=ilab@123 latency=0 buffer-mode=auto ! decodebin ! videoconvert ! appsink", cv2.CAP_GSTREAMER)
            
            # self.stream = cv2.VideoCapture("filesrc location={} latency=0 buffer-mode=auto ! decodebin ! videoconvert ! appsink".format(self.src), cv2.CAP_GSTREAMER)

            self.grabbed, self.frame = self.stream.read()

        fps = self.stream.get(cv2.CAP_PROP_FPS)
        try:
            self.wait_time = (1 / fps) / 1.1
        except Exception as e:
            self.wait_time = 0.03

        self.resolution = (int(self.stream.get(3)), int(self.stream.get(4)))

        if self.local:
            property_id = int(cv2.CAP_PROP_FRAME_COUNT)
            self.length = int(cv2.VideoCapture.get(self.stream, property_id))


    def __reconnect(self):
        self.stream.release()
        self.__connect()


    def run(self):

        self.__connect()

        frame_counter = 0

        while True:

            if not self.grabbed:
                logging.info("reconnecting to '{}'".format(self.src))
                self.__reconnect()

            if self.local:
                if frame_counter == self.length - 30:
                    logging.debug("Replaying local video '{}'".format(self.src))
                    frame_counter = 0
                    self.stream.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_counter += 1

            if self.q:
                self.frames.put(self.frame)
            sleep(self.wait_time)
            self.grabbed, self.frame = self.stream.read()
            
            ##############
            # print("\x1b[31;20mRunning test on static image instead of video source....")
            # self.frame = cv2.imread('/home/tests/test.jpeg')


    def start(self, non_blocking=True):

        if non_blocking:
            logging.info("starting video fetcher for source '{}' in non-blocking mode".format(self.src))
            t = Thread(target=self.run, args=(), daemon=True).start()

        else:
            logging.info("starting video fetcher for source '{}' in blocking mode".format(self.src))
            self.run()


    def stop(self):
        try:
            logging.info("closing connection...")
            self.stream.release()
            self.stopped = True
        except Exception as e:
            print(e)


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    fetcher = VideoFetcher(src = '/home/sanjay/Documents/RTVTR/PROJECTS/RTVTR/rtvtr/tests/test2.MP4', local=True)
    fetcher.start(non_blocking=False)
