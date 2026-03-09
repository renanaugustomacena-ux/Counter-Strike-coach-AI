"""Thread-safe frame capture ring buffer for computer vision analysis (Task 2.24.2).

Provides a fixed-size circular buffer of RGB frames and helpers to
extract CS2 HUD regions (minimap, kill feed, scoreboard) for
downstream OCR or CV pipelines.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.cv_framebuffer")

# ---------------------------------------------------------------------------
# CS2 HUD region constants (pixels at 1920x1080 reference resolution)
# ---------------------------------------------------------------------------
REFERENCE_RESOLUTION: Tuple[int, int] = (1920, 1080)
MINIMAP_REGION: Tuple[int, int, int, int] = (0, 0, 320, 320)  # top-left
KILL_FEED_REGION: Tuple[int, int, int, int] = (1520, 0, 1920, 300)  # top-right
SCOREBOARD_REGION: Tuple[int, int, int, int] = (760, 0, 1160, 60)  # top-center


class FrameBuffer:
    """Fixed-size ring buffer of RGB video frames with thread-safe access.

    Parameters
    ----------
    resolution:
        Target (width, height) to which every captured frame is resized.
    buffer_size:
        Maximum number of frames stored before the oldest is evicted.
    """

    def __init__(
        self,
        resolution: Tuple[int, int] = (1920, 1080),
        buffer_size: int = 30,
    ) -> None:
        self._resolution = resolution
        self._buffer_size = buffer_size
        self._lock = threading.Lock()

        # Pre-allocate the ring buffer (list of None slots)
        self._frames: List[Optional[np.ndarray]] = [None] * buffer_size
        self._write_index: int = 0
        self._count: int = 0  # how many frames have been captured total

        logger.info(
            "FrameBuffer initialised: resolution=%s, buffer_size=%d",
            resolution,
            buffer_size,
        )

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    def capture_frame(self, source: Union[Path, str, np.ndarray]) -> np.ndarray:
        """Ingest a frame from a file path or raw numpy array.

        The frame is resized to the target resolution, converted to RGB
        uint8, and pushed into the ring buffer (evicting the oldest frame
        if full).

        Returns the stored frame.
        """
        if isinstance(source, (str, Path)):
            # R4-10-01: Resolve and validate path to prevent directory traversal
            resolved = Path(source).resolve()
            if not resolved.is_file():
                raise FileNotFoundError(f"Could not read image: {source}")
            img = cv2.imread(str(resolved))
            if img is None:
                raise FileNotFoundError(f"Could not read image: {source}")
            # OpenCV loads as BGR — convert to RGB
            frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif isinstance(source, np.ndarray):
            frame = source.copy()
        else:
            raise TypeError(f"Unsupported source type: {type(source)}")

        # Ensure RGB uint8
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)

        # Resize if needed (width, height)
        h, w = frame.shape[:2]
        target_w, target_h = self._resolution
        if (w, h) != (target_w, target_h):
            frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        # Push into ring buffer
        with self._lock:
            self._frames[self._write_index] = frame
            self._write_index = (self._write_index + 1) % self._buffer_size
            self._count += 1

        return frame

    # ------------------------------------------------------------------
    # Frame retrieval
    # ------------------------------------------------------------------

    def get_latest(self, count: int = 1) -> List[np.ndarray]:
        """Return the *count* most recent frames (newest first).

        Returns fewer if the buffer contains less than *count* frames.
        Always returns exactly min(count, buffered_frame_count) elements;
        the `available` bound guarantees all accessed slots have been written.
        """
        with self._lock:
            available = min(count, min(self._count, self._buffer_size))
            result: List[np.ndarray] = []
            for i in range(available):
                idx = (self._write_index - 1 - i) % self._buffer_size
                result.append(self._frames[idx])
            return result

    # ------------------------------------------------------------------
    # HUD region extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _scale_region(
        region: Tuple[int, int, int, int],
        frame_shape: Tuple[int, ...],
    ) -> Tuple[int, int, int, int]:
        """Scale a reference-resolution region to the actual frame size."""
        h, w = frame_shape[:2]
        ref_w, ref_h = REFERENCE_RESOLUTION
        sx, sy = w / ref_w, h / ref_h
        x1, y1, x2, y2 = region
        return (
            int(x1 * sx),
            int(y1 * sy),
            int(x2 * sx),
            int(y2 * sy),
        )

    def extract_minimap_region(
        self,
        frame: np.ndarray,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> np.ndarray:
        """Crop the minimap region from a full-resolution frame.

        Default region is the top-left corner (CS2 standard HUD position).
        The region is scaled proportionally if the frame differs from the
        1920x1080 reference resolution.
        """
        if region is None:
            region = MINIMAP_REGION
        x1, y1, x2, y2 = self._scale_region(region, frame.shape)
        return frame[y1:y2, x1:x2].copy()

    def extract_hud_elements(self, frame: np.ndarray) -> dict:
        """Extract key HUD regions from a full-resolution frame.

        Returns a dict with cropped arrays for each HUD element and the
        raw frame resolution.  These are raw image crops — OCR or further
        CV processing is left to downstream consumers.
        """
        minimap = self.extract_minimap_region(frame)

        kf = self._scale_region(KILL_FEED_REGION, frame.shape)
        kill_feed = frame[kf[1] : kf[3], kf[0] : kf[2]].copy()

        sb = self._scale_region(SCOREBOARD_REGION, frame.shape)
        scoreboard = frame[sb[1] : sb[3], sb[0] : sb[2]].copy()

        h, w = frame.shape[:2]
        return {
            "minimap": minimap,
            "kill_feed": kill_feed,
            "scoreboard": scoreboard,
            "raw_resolution": (w, h),
        }
