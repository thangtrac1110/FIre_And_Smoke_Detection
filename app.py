import os
import time
import threading
from collections import defaultdict

import cv2
import yaml
from flask import Flask, Response, jsonify, render_template, request
from ultralytics import YOLO

from captures import create_capture

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "config.yaml"), "r") as f:
    config = yaml.safe_load(f)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "uploads")

model = YOLO(os.path.join(BASE_DIR, config["model"]["path"]))

current_capture = None
current_capture_lock = threading.Lock()
current_source = None

metrics_lock = threading.Lock()
metrics_data = {
    "fps": 0.0,
    "total_detections": 0,
    "class_counts": {},
    "lowest_confidence": 0.0,
    "conf": 0.25,
    "iou": 0.7,
}
_frame_times = []


def update_metrics(fps, total, class_counts, lowest_conf):
    with metrics_lock:
        metrics_data["fps"] = round(fps, 1)
        metrics_data["total_detections"] = total
        metrics_data["class_counts"] = class_counts
        metrics_data["lowest_confidence"] = round(lowest_conf, 4) if lowest_conf < 1.0 else 1.0


def release_capture():
    global current_capture, current_source
    with current_capture_lock:
        if current_capture is not None:
            current_capture.release()
            current_capture = None
        current_source = None


def open_capture(source_type, source_value=None):
    global current_capture, current_source
    release_capture()
    try:
        cap = create_capture(source_type, source_value)
    except ValueError:
        return False

    if not cap.isOpened():
        cap.release()
        return False

    current_capture = cap
    current_source = source_type
    return True


def generate_frames():
    global _frame_times
    _frame_times = []
    class_names = model.names

    while True:
        with current_capture_lock:
            if current_capture is None or not current_capture.isOpened():
                time.sleep(0.1)
                continue
            cap = current_capture

        with metrics_lock:
            conf = metrics_data["conf"]
            iou = metrics_data["iou"]

        success, frame = cap.read()
        if not success:
            time.sleep(0.1)
            continue

        results = model.predict(frame, conf=conf, iou=iou, verbose=False)
        annotated_frame = results[0].plot()

        now = time.time()
        _frame_times.append(now)
        _frame_times[:] = [t for t in _frame_times if now - t < 3.0]
        fps = len(_frame_times) / 3.0 if len(_frame_times) > 1 else 0.0

        boxes = results[0].boxes
        total = len(boxes)
        class_counts = defaultdict(int)
        lowest_conf = 1.0
        if total > 0:
            for box in boxes:
                cls_id = int(box.cls[0])
                class_counts[class_names.get(cls_id, str(cls_id))] += 1
                conf_val = float(box.conf[0])
                if conf_val < lowest_conf:
                    lowest_conf = conf_val
        else:
            lowest_conf = 0.0

        update_metrics(fps, total, dict(class_counts), lowest_conf)

        ret, buffer = cv2.imencode(".jpg", annotated_frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


@app.route("/")
def index():
    images_cfg = config.get("images", {})
    public_cfg = config.get("public_camera", {})
    return render_template(
        "index.html",
        default_url=config["ip_webcam"]["default_url"],
        logo_url=images_cfg.get("logo", ""),
        hero_bg_url=images_cfg.get("hero_bg", ""),
        public_camera_url=public_cfg.get("default_stream_url", ""),
        public_camera_name=public_cfg.get("name", "Public Camera"),
    )


@app.route("/check_stream", methods=["GET"])
def check_stream():
    url = request.args.get("url", config["ip_webcam"]["default_url"])
    cap = cv2.VideoCapture(url)
    success = cap.isOpened()
    if success:
        cap.release()
    return jsonify({"success": success})


@app.route("/video_feed")
def video_feed():
    source = request.args.get("source", "webcam")
    url = request.args.get("url", config["ip_webcam"]["default_url"])
    path = request.args.get("path", "")
    conf = float(request.args.get("conf", 0.25))
    iou = float(request.args.get("iou", 0.7))

    with metrics_lock:
        metrics_data["conf"] = conf
        metrics_data["iou"] = iou

    if source == "ip":
        if not open_capture("ip", url):
            return jsonify({"error": "Failed to open IP Webcam stream"}), 400
    elif source == "webcam":
        if not open_capture("webcam"):
            return jsonify({"error": "Failed to open device webcam"}), 400
    elif source == "file":
        full_path = os.path.join(app.config["UPLOAD_FOLDER"], path)
        if not os.path.exists(full_path):
            return jsonify({"error": "File not found"}), 404
        if not open_capture("file", full_path):
            return jsonify({"error": "Failed to open video file"}), 400
    elif source == "public":
        if not open_capture("url", url):
            return jsonify({"error": "Failed to open public camera stream"}), 400
    else:
        return jsonify({"error": f"Unknown source: {source}"}), 400

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/update_params", methods=["POST"])
def update_params():
    conf = float(request.args.get("conf", metrics_data["conf"]))
    iou = float(request.args.get("iou", metrics_data["iou"]))
    with metrics_lock:
        metrics_data["conf"] = conf
        metrics_data["iou"] = iou
    return jsonify({"success": True, "conf": conf, "iou": iou})


@app.route("/metrics", methods=["GET"])
def get_metrics():
    with metrics_lock:
        return jsonify(dict(metrics_data))


@app.route("/upload", methods=["POST"])
def upload():
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    return jsonify({"filename": file.filename})


@app.route("/stop_stream", methods=["POST"])
def stop_stream():
    release_capture()
    with metrics_lock:
        metrics_data["fps"] = 0.0
        metrics_data["total_detections"] = 0
        metrics_data["class_counts"] = {}
        metrics_data["lowest_confidence"] = 0.0
    return jsonify({"success": True})


if __name__ == "__main__":
    server_cfg = config["server"]
    app.run(
        host=server_cfg["host"],
        port=server_cfg["port"],
        debug=server_cfg["debug"],
    )