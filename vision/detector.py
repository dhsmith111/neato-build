"""Object detection using YOLOv8 on Hailo-10H NPU."""

import os
import numpy as np
from PIL import Image
from picamera2.devices import Hailo


# COCO class names (80 classes) — standard YOLOv8 output order
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush"
]


class Detection:
    """A single detected object."""

    __slots__ = ('class_id', 'label', 'confidence', 'x_min', 'y_min', 'x_max', 'y_max')

    def __init__(self, class_id, confidence, x_min, y_min, x_max, y_max):
        self.class_id = class_id
        self.label = COCO_CLASSES[class_id]
        self.confidence = confidence
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max

    def __repr__(self):
        return (f"Detection({self.label}, {self.confidence:.0%}, "
                f"({self.x_min:.3f},{self.y_min:.3f})-({self.x_max:.3f},{self.y_max:.3f}))")

    def box_pixels(self, img_width, img_height):
        """Return bounding box in pixel coordinates: (left, top, right, bottom)."""
        return (
            int(self.x_min * img_width),
            int(self.y_min * img_height),
            int(self.x_max * img_width),
            int(self.y_max * img_height),
        )


class Detector:
    """YOLOv8 object detector running on Hailo-10H.

    Uses the picamera2 Hailo wrapper which handles the async InferModel API.
    The old InferVStreams API does not work on Hailo-10H (hailort 5.x).
    """

    DEFAULT_MODEL = "/usr/share/hailo-models/yolov8m_h10.hef"

    def __init__(self, model_path=None, confidence_threshold=0.5):
        self.model_path = model_path or self.DEFAULT_MODEL
        self.confidence_threshold = confidence_threshold
        self.hailo = None
        self.model_width = None
        self.model_height = None

    def start(self):
        """Load model onto Hailo-10H."""
        self.hailo = Hailo(self.model_path)
        self.model_height, self.model_width, _ = self.hailo.get_input_shape()

    def detect(self, frame):
        """Run detection on a single frame.

        Args:
            frame: RGB uint8 numpy array, any size (will be resized).

        Returns:
            list[Detection]: Detections above confidence threshold.
        """
        if not self.hailo:
            raise RuntimeError("Detector not started — call start() first")

        # Resize to model input
        if frame.shape[0] != self.model_height or frame.shape[1] != self.model_width:
            frame = np.array(Image.fromarray(frame).resize(
                (self.model_width, self.model_height)))

        results = self.hailo.run(frame)
        return self._parse_results(results)

    def _parse_results(self, results):
        """Parse Hailo output into Detection objects.

        Output format: list of 80 arrays (one per COCO class), each (N, 5)
        where each row is [y_min, x_min, y_max, x_max, confidence].
        Coordinates are normalized 0-1.
        """
        detections = []
        if not isinstance(results, list) or len(results) != 80:
            return detections

        for class_id, class_dets in enumerate(results):
            if class_dets.shape[0] == 0:
                continue
            for det in class_dets:
                confidence = float(det[4])
                if confidence >= self.confidence_threshold:
                    detections.append(Detection(
                        class_id=class_id,
                        confidence=confidence,
                        x_min=float(det[1]),
                        y_min=float(det[0]),
                        x_max=float(det[3]),
                        y_max=float(det[2]),
                    ))

        # Sort by confidence descending
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections

    def stop(self):
        """Release the Hailo device.

        Note: Hailo VDevice cleanup may log errors — this is a known issue
        with h10-hailort 5.1.1 and does not affect inference results.
        """
        if self.hailo:
            try:
                self.hailo.close()
            except Exception:
                pass
            self.hailo = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()