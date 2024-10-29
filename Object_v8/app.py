from flask import Flask, Response, jsonify
import cv2
from ultralytics import YOLO
import json
from collections import deque
from datetime import datetime
import threading
import time

app = Flask(__name__)


# Global variables for tracking statistics
class DetectionStats:
    def __init__(self):
        self.total_objects = 0
        self.confidence_sum = 0
        self.detection_history = deque(maxlen=50)  # Keep last 50 detections
        self.fps = 0
        self.is_detecting = True
        self.lock = threading.Lock()


stats = DetectionStats()

# Load YOLO model
model = YOLO("yolov8n.pt")


def calculate_fps():
    """Calculate FPS in a separate thread"""
    frame_count = 0
    start_time = time.time()

    while True:
        if frame_count == 30:  # Update FPS every 30 frames
            end_time = time.time()
            stats.fps = frame_count / (end_time - start_time)
            frame_count = 0
            start_time = time.time()
        frame_count += 1
        time.sleep(0.001)  # Small sleep to prevent excessive CPU usage


# Start FPS calculation thread
fps_thread = threading.Thread(target=calculate_fps, daemon=True)
fps_thread.start()


def detect_objects():
    """Generator function for video streaming with object detection"""
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if stats.is_detecting:
            # Perform object detection
            results = model(frame)
            detections = results[0].boxes

            # Update statistics
            with stats.lock:
                frame_detections = []
                frame_confidence_sum = 0

                for det in detections:
                    x1, y1, x2, y2 = map(int, det.xyxy[0])
                    confidence = det.conf[0].item()
                    class_id = int(det.cls[0].item())
                    label = f"{model.names[class_id]}: {confidence * 100:.2f}%"

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        label,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2,
                    )

                    frame_detections.append(
                        {"class": model.names[class_id], "confidence": confidence * 100}
                    )
                    frame_confidence_sum += confidence * 100

                num_detections = len(frame_detections)
                stats.total_objects += num_detections
                stats.confidence_sum += frame_confidence_sum

                if num_detections > 0:
                    stats.detection_history.appendleft(
                        {
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "objects": frame_detections,
                        }
                    )

        ret, buffer = cv2.imencode(".jpg", frame)
        frame = buffer.tobytes()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n\r\n")

    cap.release()


@app.route("/video_feed")
def video_feed():
    return Response(
        detect_objects(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/stats")
def get_stats():
    with stats.lock:
        avg_confidence = (
            stats.confidence_sum / stats.total_objects if stats.total_objects > 0 else 0
        )
        return jsonify(
            {
                "total_objects": stats.total_objects,
                "avg_confidence": round(avg_confidence, 2),
                "fps": round(stats.fps, 1),
                "detection_history": list(stats.detection_history),
                "is_detecting": stats.is_detecting,
            }
        )


@app.route("/toggle_detection/<state>")
def toggle_detection(state):
    stats.is_detecting = state == "true"
    return jsonify({"success": True})


@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Object Detection Dashboard</title>
    <style>
        /* CSS for styling */
        .navbar { background-color: #333; color: #fff; padding: 1rem; text-align: center; }
        .container { display: flex; gap: 1rem; padding: 1rem; }
        .video-container { flex: 2; position: relative; }
        .video-feed { width: 100%; border-radius: 8px; }
        #fps-meter { position: absolute; top: 10px; left: 10px; background: rgba(0, 0, 0, 0.7); color: #fff; padding: 5px; border-radius: 4px; }
        .controls { display: flex; gap: 10px; margin-top: 10px; }
        .button { padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; }
        .primary { background-color: #007bff; color: white; }
        .danger { background-color: #dc3545; color: white; }
        .stats-panel { flex: 1; border: 1px solid #ddd; padding: 1rem; border-radius: 8px; }
        .stat-card { margin: 10px 0; }
        .stat-title { font-size: 0.9rem; color: #888; }
        .stat-value { font-size: 1.5rem; color: #333; }
        .detection-list { max-height: 150px; overflow-y: auto; }
    </style>
</head>
<body>
    <nav class="navbar">
        <h1>AI Object Detection Dashboard</h1>
    </nav>
    <div class="container">
        <div class="video-container">
            <img src="/video_feed" class="video-feed" alt="Video Feed" id="video-feed">
            <div id="fps-meter">FPS: <span id="fps-value">0</span></div>
            <div class="controls">
                <button class="button primary" id="start-btn">Start Detection</button>
                <button class="button danger" id="stop-btn">Stop Detection</button>
            </div>
        </div>
        <div class="stats-panel">
            <h2>Detection Statistics</h2>
            <div class="stat-card">
                <div class="stat-title">Objects Detected</div>
                <div class="stat-value" id="objects-count">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Average Confidence</div>
                <div class="stat-value" id="avg-confidence">0%</div>
            </div>
            <div class="detection-list" id="detection-list">
                <!-- Detection items added dynamically -->
            </div>
        </div>
    </div>
    <script>
        let isDetecting = true;
        function updateStats() {
            fetch('/stats').then(response => response.json()).then(data => {
                document.getElementById('objects-count').textContent = data.total_objects;
                document.getElementById('avg-confidence').textContent = `${data.avg_confidence}%`;
                document.getElementById('fps-value').textContent = data.fps;
                const detectionList = document.getElementById('detection-list');
                detectionList.innerHTML = '';
                data.detection_history.forEach(detection => {
                    const detectionItem = document.createElement('div');
                    detectionItem.className = 'detection-item';
                    const objects = detection.objects.map(obj => `${obj.class} (${obj.confidence.toFixed(1)}%)`).join(', ');
                    detectionItem.innerHTML = `<span>${detection.timestamp}</span><span>${objects}</span>`;
                    detectionList.appendChild(detectionItem);
                });
            });
        }
        setInterval(updateStats, 1000);
        document.getElementById('start-btn').onclick = function() {
            fetch('/toggle_detection/true').then(() => {
                isDetecting = true;
                this.disabled = true;
                document.getElementById('stop-btn').disabled = false;
            });
        };
        document.getElementById('stop-btn').onclick = function() {
            fetch('/toggle_detection/false').then(() => {
                isDetecting = false;
                this.disabled = true;
                document.getElementById('start-btn').disabled = false;
            });
        };
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    app.run(debug=True)
