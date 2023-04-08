import os
from os.path import expanduser
from time import sleep
import asyncio
import logging
import numpy as np
import cv2
import uvicorn

from helper import retrieve_best_interpolation, reducer, generate_webdata

from starlette.routing import Mount, Route
from starlette.responses import StreamingResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from starlette.applications import Starlette

import simplejpeg

from video_fetcher import VideoFetcher
from config import camera_list


TEST_SRC = None


class Streamer:
    
    def __init__(
        self, 
        sources={},
        framerate = 25,
        logging = True,
        time_delay = 0,
        update_sources = None,
        resolution = (640,480),
        **options
    ):
        self.sources = sources
        self.framerate = framerate
        self.logging = logging
        self.time_delay = time_delay
        self.update_sources = update_sources
        self.resolution = resolution
        self.__jpeg_compression_quality = 60  # 90% quality
        self.__jpeg_compression_fastdct = True  # fastest DCT on by default
        self.__jpeg_compression_colorspace = "BGR"  # use BGR colorspace by default
        self.__logging = logging
        self.__frame_size_reduction = 0  # use 25% reduction
        self.__enable_inf = True
        
        self.streams = {}
        
        # retrieve interpolation for reduction
        self.__interpolation = retrieve_best_interpolation(
            ["INTER_LINEAR_EXACT", "INTER_LINEAR", "INTER_AREA"]
        )

        options = {str(k).strip(): v for k, v in options.items()}
        
        if options:
            if "jpeg_compression_quality" in options:
                value = options["jpeg_compression_quality"]
                # set valid jpeg quality
                if isinstance(value, (int, float)) and value >= 10 and value <= 100:
                    self.__jpeg_compression_quality = int(value)
                else:
                    logging.warning("Skipped invalid `jpeg_compression_quality` value!")
                del options["jpeg_compression_quality"]

            if "frame_size_reduction" in options:
                value = options["frame_size_reduction"]
                if isinstance(value, (int, float)) and value >= 0 and value <= 90:
                    self.__frame_size_reduction = value
                else:
                    logging.warning("Skipped invalid `frame_size_reduction` value!")
                del options["frame_size_reduction"]

            if "enable_infinite_frames" in options:
                value = options["enable_infinite_frames"]
                if isinstance(value, bool):
                    self.__enable_inf = value
                else:
                    logging.warning("Skipped invalid `enable_infinite_frames` value!")
                del options["enable_infinite_frames"]

        data_path = generate_webdata(
                os.path.join(expanduser("~"), ".vidgear"),
                c_name="webgear",
                overwrite_default=False,
                logging=logging,
            )

        self.__templates = Jinja2Templates(directory="{}/templates".format(data_path))

        self.routes = [
            Route("/", endpoint=self.__homepage),
            Route("/video/{streaming_channel}/{cam_id}", endpoint = self.__video),
            Mount(
                "/static",
                app=StaticFiles(directory="{}/static".format(data_path)),
                name="static",
            ),
        ]
        
        self.middleware = []

        self.__isrunning = True
        self.blank_frame = None


    def __call__(self):
        """
        Implements a custom Callable method for WebGear application.
        """

        # initiate stream
        self.__logging and logging.debug("Initiating Video Streaming.")

        # return Starlette application
        self.__logging and logging.debug("Running Starlette application.")
        return Starlette(
            debug=(True if self.__logging else False),
            routes=self.routes,
            middleware=self.middleware,
            exception_handlers={},
            on_shutdown=[self.shutdown],
        )
        

    async def __video(self, scope):
        """
        Return a async video streaming response.
        """
        assert scope["type"] in ["http", "https"]

        cam_id = int(float(scope.path_params['cam_id']))
        streaming_channel = scope.path_params['streaming_channel']

        print('cam_id: ', cam_id)
        print('streaming_channel: ', streaming_channel)
        
        if self.update_sources is not None:
            self.sources = self.update_sources()
        
        try:
            if streaming_channel == 'primary':
                source = self.sources[cam_id]['primary_source']
            else:
                source = self.sources[cam_id]['secondary_source']

        except Exception as e:
            self.__logging and logging.error(f"Source not found for camera id '{cam_id}' and \
                streaming channel '{streaming_channel}'\nError: {str(e)}")
            source = None

        return StreamingResponse(
            self.__producer(cam_id, source),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )
        
        
    def create_blank_frame(self, shape=None, text="", logging=False):
        """
        ## create_blank_frame

        Create blank frames of given frame size with text

        Parameters:
            frame (numpy.ndarray): inputs numpy array(frame).
            text (str): Text to be written on frame.
        **Returns:**  A reduced numpy ndarray array.
        """
        # grab the frame size
        (width, height) = shape
        # create blank frame
        blank_frame = np.zeros((height, width, 3), np.uint8)
        # setup text
        if text and isinstance(text, str):
            # setup font
            font = cv2.FONT_HERSHEY_SCRIPT_COMPLEX
            # get boundary of this text
            fontScale = min(height, width) / (25 / 0.25)
            textsize = cv2.getTextSize(text, font, fontScale, 2)[0]
            # get coords based on boundary
            textX = (width - textsize[0]) // 2
            textY = (height + textsize[1]) // 2
            # put text
            cv2.putText(
                blank_frame, text, (textX, textY), font, fontScale, (125, 125, 125), 3
            )

        # return frame
        return blank_frame        


    async def __producer(self, cam_id, source):
        """
        WebGear's default asynchronous frame producer/generator.
        """
        wait_for_frame = 50

        try:
            print("getting source stream...")
            stream = self.streams[source]
            print(stream)
        except KeyError as e:
            print("creating new stream...")
            stream = VideoFetcher(src=source, cam_id=cam_id, q=False)
            self.streams[source] = stream

            if not (stream is None):
                stream.start(non_blocking=True)

        # loop over frames
        while self.__isrunning:
            # read frame
            frame = stream.frame
            # print("frame: ", frame)
            # display blank if NoneType
            if frame is None: 
                if wait_for_frame > 0:
                    wait_for_frame -= 1
                    await asyncio.sleep(0.03)
                    # print("wait for frame: ", wait_for_frame)
                    continue

                if self.blank_frame is None:
                    self.blank_frame = self.create_blank_frame(
                        shape=self.resolution,
                        text="No Input" if self.__enable_inf else "The End",
                        logging=self.__logging,
                    )
            
                frame = (
                    self.blank_frame
                    if self.blank_frame is None
                    else self.blank_frame[:]
                )
                if not self.__enable_inf:
                    self.__isrunning = False

            else:
                wait_for_frame = 50

            # reducer frames size if specified
            if self.__frame_size_reduction:
                frame = await reducer(
                    frame,
                    percentage=self.__frame_size_reduction,
                    interpolation=self.__interpolation,
                )

            # handle JPEG encoding
            encodedImage = simplejpeg.encode_jpeg(
                frame,
                quality=self.__jpeg_compression_quality,
                colorspace=self.__jpeg_compression_colorspace,
                colorsubsampling="422",
                fastdct=self.__jpeg_compression_fastdct,
            )

            # yield frame in byte format
            yield (
                b"--frame\r\nContent-Type:image/jpeg\r\n\r\n" + encodedImage + b"\r\n"
            )
            # sleep for sometime.
            await asyncio.sleep(0.075)
            
        stream.stop()

            
    async def __homepage(self, request):
        """
        Return an HTML index page.
        """
        return self.__templates.TemplateResponse("index.html", {"request": request})
    
    
    def shutdown(self):
        """
        Implements a Callable to be run on application shutdown
        """
        self.__isrunning = False


def __get_sources():
    
    cameras = camera_list

    sources = {}
    
    for camera in cameras:
        cam_id = camera["id"]

        primary_source = "{}://{}:{}@{}:{}{}".format(camera["protocol"], camera["username"], camera["password"],
                    camera["ip"], camera["port"], camera["primary_channel_uri"])
        secondary_source = "{}://{}:{}@{}:{}{}".format(camera["protocol"], camera["username"], camera["password"],
                    camera["ip"], camera["port"], camera["secondary_channel_uri"])


        if camera["primary_streaming_url"]:
            primary_source = camera["primary_streaming_url"]
            
        if camera["secondary_streaming_url"]:
            secondary_source = camera["secondary_streaming_url"]

        primary_source = TEST_SRC if TEST_SRC else primary_source
        secondary_source = TEST_SRC if TEST_SRC else secondary_source
        
        print(primary_source)
        print(secondary_source)

        sources[cam_id] = {
            "primary_source": primary_source,
            "secondary_source": secondary_source
        }

    return sources



if __name__=='__main__':
    # streamer = Streamer(source="rtsp://admin:Nepal@123@192.168.1.2:554/Streaming/channels/102", cam_id=1)
    # # streamer = Streamer(source="/home/laanta/Documents/INTELLETICS/intelletics-core-edge-backend/rtvtr/tests/test3.MP4", cam_id=1)
    # uvicorn.run(streamer(), host="localhost", port=8000)
    # streamer.shutdown()

    sources = __get_sources()

    streamer = Streamer(sources=sources, update_sources = __get_sources)
    uvicorn.run(streamer(), host="0.0.0.0", port=8001)
    streamer.shutdown()
