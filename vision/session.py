"""Capture session management — timestamped folders under captures/."""

import os
from datetime import datetime
from PIL import Image, ImageDraw


CAPTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "captures")


class Session:
    """Manages a capture session with timestamped output folder.

    Usage:
        session = Session("drive-test")
        session.save(frame, detections, label="start")
        session.save(frame, detections, label="fwd-200mm")
    """

    def __init__(self, name="session"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.name = f"{timestamp}_{name}"
        self.dir = os.path.join(CAPTURES_DIR, self.name)
        os.makedirs(self.dir, exist_ok=True)
        self.frame_num = 0

    def save(self, frame, detections=None, label=""):
        """Save a frame with optional detection overlay.

        Args:
            frame: RGB uint8 numpy array.
            detections: list of Detection objects (optional).
            label: descriptive label for the frame.

        Returns:
            str: Path to saved image.
        """
        img = Image.fromarray(frame)

        if detections:
            draw = ImageDraw.Draw(img)
            w, h = img.size
            for d in detections:
                left, top, right, bottom = d.box_pixels(w, h)
                draw.rectangle([left, top, right, bottom], outline="lime", width=3)
                draw.text((left + 4, top + 4),
                          f"{d.label} {d.confidence:.0%}", fill="lime")

        suffix = f"_{label}" if label else ""
        filename = f"frame_{self.frame_num:03d}{suffix}.jpg"
        path = os.path.join(self.dir, filename)
        img.save(path)
        self.frame_num += 1
        return path

    def summary_path(self):
        """Return path for a text summary file."""
        return os.path.join(self.dir, "summary.txt")