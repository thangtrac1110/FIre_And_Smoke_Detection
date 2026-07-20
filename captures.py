import threading
import subprocess
import numpy as np
import cv2


class BaseCapture:
    """Base class for all video capture sources."""

    def read(self):
        raise NotImplementedError

    def isOpened(self):
        raise NotImplementedError

    def release(self):
        raise NotImplementedError


class OpenCVcapture(BaseCapture):
    """Wraps a cv2.VideoCapture for standard sources (webcam, IP camera, file, MJPEG)."""

    def __init__(self, source, index_or_path=None):
        if index_or_path is not None:
            self._cap = cv2.VideoCapture(index_or_path)
        else:
            self._cap = cv2.VideoCapture(source)
        self._source = source

    def read(self):
        return self._cap.read()

    def isOpened(self):
        return self._cap.isOpened()

    def release(self):
        self._cap.release()


class HLSVideoCapture(BaseCapture):
    """Reads HLS streams via imageio-ffmpeg's bundled FFmpeg subprocess, returning frames
    compatible with OpenCV. Falls back to direct OpenCV HLS support if available.
    """

    def __init__(self, hls_url, ffmpeg_path=None):
        self._hls_url = hls_url
        self._proc = None
        self._frame_size = 0
        self._frame_width = 0
        self._frame_height = 0
        self._buffer = b""
        self._lock = threading.Lock()
        self._dead = False
        self._start(ffmpeg_path)

    def _start(self, ffmpeg_path=None):
        if ffmpeg_path is None:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        cmd = [
            ffmpeg_path,
            "-threads", "4",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-i", self._hls_url,
            "-vf", "scale=1280:-2",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-loglevel", "error",
            "-"
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=10 ** 8
        )

    def read(self):
        if self._proc is None or self._proc.poll() is not None:
            return False, None

        while len(self._buffer) < (self._frame_size or 1):
            chunk = self._proc.stdout.read(8192)
            if not chunk:
                return False, None
            self._buffer += chunk

            if self._frame_size == 0 and len(self._buffer) >= 12:
                w_bytes = self._buffer[4:8]
                h_bytes = self._buffer[8:12]
                try:
                    raw_w = np.frombuffer(w_bytes, dtype=np.int32, count=1)[0]
                    raw_h = np.frombuffer(h_bytes, dtype=np.int32, count=1)[0]
                    if 0 < raw_w < 10000 and 0 < raw_h < 10000:
                        self._frame_width = raw_w
                        self._frame_height = raw_h
                        self._frame_size = self._frame_width * self._frame_height * 3
                        self._buffer = self._buffer[12:]
                        break
                except Exception:
                    pass

            if self._frame_size == 0 and len(self._buffer) > 8192 * 4:
                self._buffer = b""

        if self._frame_size > 0 and len(self._buffer) >= self._frame_size:
            raw = self._buffer[:self._frame_size]
            self._buffer = self._buffer[self._frame_size:]
            frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                (self._frame_height, self._frame_width, 3)
            )
            return True, frame

        return False, None

    def isOpened(self):
        return self._proc is not None and self._proc.poll() is None

    def release(self):
        self._dead = True
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None


def create_capture(source_type, source_value=None):
    """Factory function that returns the appropriate capture instance."""

    if source_type == "webcam":
        return OpenCVcapture(0)
    elif source_type == "ip":
        return OpenCVcapture(source_value)
    elif source_type == "file":
        return OpenCVcapture(source_value)
    elif source_type == "hls":
        return HLSVideoCapture(source_value)
    elif source_type == "url":
        return OpenCVcapture(source_value)
    else:
        raise ValueError(f"Unknown source type: {source_type}")