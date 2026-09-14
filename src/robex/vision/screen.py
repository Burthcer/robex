"""High-performance screen capture module using mss and Pillow."""

import logging
from typing import Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

try:
    import mss
    HAS_MSS = True
except ImportError:
    mss = None
    HAS_MSS = False

try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    Image = None
    ImageGrab = None
    HAS_PIL = False


class ScreenGrabber:
    """Captures desktop or region screenshots at high frame rates."""

    def __init__(self):
        mss_factory = getattr(mss, "MSS", getattr(mss, "mss", None)) if HAS_MSS else None
        self._sct = mss_factory() if mss_factory else None

    def grab_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """Captures screen as a BGR/RGB numpy array for OpenCV processing.

        Args:
            region: Optional tuple of (left, top, width, height).
        """
        if HAS_MSS and self._sct:
            try:
                if region:
                    left, top, width, height = region
                    monitor = {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}
                else:
                    # Monitor 1 is primary display
                    monitor = self._sct.monitors[1] if len(self._sct.monitors) > 1 else self._sct.monitors[0]

                sct_img = self._sct.grab(monitor)
                # sct_img is BGRA, convert to BGR numpy array
                frame = np.array(sct_img)
                return frame[:, :, :3]
            except Exception as e:
                logger.error("mss grab failed: %s", e)

        if HAS_PIL and ImageGrab:
            try:
                bbox = (region[0], region[1], region[0] + region[2], region[1] + region[3]) if region else None
                img = ImageGrab.grab(bbox=bbox)
                # PIL is RGB, convert to BGR for OpenCV standard
                rgb_arr = np.array(img)
                return rgb_arr[:, :, ::-1]
            except Exception as e:
                logger.error("PIL ImageGrab failed: %s", e)

        return None

    def save_snapshot(self, filepath: str, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """Saves current screen snapshot to file."""
        frame = self.grab_screen(region)
        if frame is None:
            return False

        try:
            import cv2
            cv2.imwrite(filepath, frame)
            return True
        except ImportError:
            if HAS_PIL and Image:
                # Convert BGR back to RGB
                rgb = frame[:, :, ::-1]
                pil_img = Image.fromarray(rgb)
                pil_img.save(filepath)
                return True
        return False

    def close(self):
        """Releases mss resources."""
        if self._sct:
            try:
                self._sct.close()
            except Exception:
                pass


# Global screen grabber instance
screen_grabber = ScreenGrabber()
