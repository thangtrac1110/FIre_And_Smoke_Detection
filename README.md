# Fire and Smoke Detection

A real-time **fire and smoke detection** web app built with Ultralytics YOLO and Flask. Each video frame is run through the model, detected fire and smoke regions are drawn with bounding boxes, and live statistics are shown in the browser.

## Features

- Multiple video sources:
  - Local webcam
  - IP camera (e.g. the **IP Webcam** app on an Android phone)
  - Uploaded video files
  - Public camera streams (MJPEG)
- Adjust **confidence** and **IoU** thresholds on the fly
- Live metrics panel: FPS, total detections, per-class counts, lowest confidence score

## Project structure

```
├── app.py            # Flask server: streaming, upload and metrics routes
├── captures.py       # Video source readers (OpenCV, HLS via FFmpeg)
├── config.yaml       # Model, camera and server settings
├── requirements.txt
├── models/
│   ├── best.pt       # Fire/smoke weights (used by default)
│   └── yolo26n.pt    # Base YOLO weights
├── static/           # CSS, JS and images
├── templates/
│   └── index.html    # Main web page
└── uploads/          # Uploaded videos and sample clips for testing
```

## Installation

Requires Python 3.10 or newer.

```bash
git clone https://github.com/thangtrac1110/FIre_And_Smoke_Detection.git
cd FIre_And_Smoke_Detection

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

Open **http://localhost:5000** in your browser, pick a video source and start the stream.

To try it without a camera, choose the **File** source and use one of the sample videos in the `uploads/` folder.

## Configuration

Edit `config.yaml`:

| Key | Description |
|---|---|
| `model.path` | Path to the YOLO weights file |
| `ip_webcam.default_url` | Default IP camera URL, e.g. `http://<phone-ip>:8080/video` |
| `public_camera.default_stream_url` | Default public camera stream |
| `server.host`, `server.port` | Server address and port |
| `server.debug` | Flask debug mode (turn off in production) |

## API

| Route | Method | Description |
|---|---|---|
| `/video_feed?source=webcam\|ip\|file\|public` | GET | Annotated MJPEG stream |
| `/upload` | POST | Upload a video (form field `video`) |
| `/update_params?conf=&iou=` | POST | Update detection thresholds |
| `/metrics` | GET | Current metrics as JSON |
| `/check_stream?url=` | GET | Check whether an IP camera is reachable |
| `/stop_stream` | POST | Stop the current stream |

## Credits

Original source code by [NhanPhan090806/FIre_And_Smoke_Detection](https://github.com/NhanPhan090806/FIre_And_Smoke_Detection).
