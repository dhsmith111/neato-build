"""Camera capture using picamera2."""

import time
import numpy as np
from picamera2 import Picamera2


class Camera:
    """Pi Camera capture for vision pipeline."""

    def __init__(self, width=640, height=640, camera_num=0):
        self.width = width
        self.height = height
        self.camera_num = camera_num
        self.picam = None

    def start(self, settle_time=2):
        """Start camera and let auto-exposure settle."""
        self.picam = Picamera2(self.camera_num)
        config = self.picam.create_preview_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"}
        )
        self.picam.configure(config)
        self.picam.start()
        if settle_time > 0:
            time.sleep(settle_time)

    def capture(self):
        """Capture a single frame as RGB uint8 numpy array.

        Returns:
            np.ndarray: Shape (height, width, 3), dtype uint8, RGB format.
        """
        if not self.picam:
            raise RuntimeError("Camera not started — call start() first")
        frame = self.picam.capture_array()
        # Drop alpha channel if present (XRGB format)
        if frame.ndim == 3 and frame.shape[2] == 4:
            frame = frame[:, :, :3]
        return frame

    def stop(self):
        """Stop and release the camera."""
        if self.picam:
            self.picam.stop()
            self.picam.close()
            self.picam = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()