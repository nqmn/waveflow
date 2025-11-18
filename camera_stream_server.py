#!/usr/bin/env python3
"""
Real-time Camera Stream Server for RISNet

Streams camera feed to web browser via HTTP.
Access at: http://localhost:8080

Usage:
    python3 camera_stream_server.py [--port 8080] [--camera 0]
"""

import cv2
import argparse
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import io

class CameraStreamHandler(BaseHTTPRequestHandler):
    """HTTP request handler for camera stream"""

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            # Serve HTML page
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>RISNet Camera Stream</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        margin: 0;
                        background-color: #f0f0f0;
                    }
                    .container {
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        text-align: center;
                    }
                    h1 { color: #333; margin: 0 0 20px 0; }
                    img { max-width: 800px; width: 100%; border: 2px solid #ddd; border-radius: 4px; }
                    .status { margin-top: 20px; font-size: 14px; color: #666; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>RISNet Camera Stream</h1>
                    <img src="/stream.mjpeg" width="800" />
                    <div class="status">
                        <p>Live camera feed from USB camera</p>
                        <p>Position your ArUco marker in the camera view</p>
                    </div>
                </div>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Content-length', len(html))
            self.end_headers()
            self.wfile.write(html.encode())

        elif self.path == '/stream.mjpeg':
            # Serve MJPEG stream
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()

            try:
                while True:
                    frame_data = camera_server.get_frame()
                    if frame_data is None:
                        time.sleep(0.01)
                        continue

                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(b'Content-length: ' + str(len(frame_data)).encode() + b'\r\n\r\n')
                    self.wfile.write(frame_data)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                print(f"Stream error: {e}")

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


class CameraServer:
    """Camera capture and stream server"""

    def __init__(self, camera_id=0, fps=30):
        self.camera_id = camera_id
        self.fps = fps
        self.cap = None
        self.current_frame = None
        self.lock = threading.Lock()
        self.running = False

    def start(self):
        """Start camera capture thread"""
        self.running = True
        self.cap = cv2.VideoCapture(self.camera_id)

        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_id}")
            return False

        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Start capture thread
        thread = threading.Thread(target=self._capture_loop, daemon=True)
        thread.start()

        print(f"Camera {self.camera_id} started at {self.fps} FPS")
        return True

    def _capture_loop(self):
        """Continuous camera capture loop with ArUco detection"""
        # Setup ArUco detector with more robust dictionary
        # DICT_5X5_100 is more reliable than DICT_4X4_50 for varied lighting conditions
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100)

        # Configure detector parameters for better robustness
        detector_params = cv2.aruco.DetectorParameters()
        detector_params.adaptiveThreshConstant = 7
        detector_params.adaptiveThreshWinSizeMin = 3
        detector_params.adaptiveThreshWinSizeMax = 23
        detector_params.adaptiveThreshWinSizeStep = 10
        detector_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
        detector_params.minMarkerPerimeterRate = 0.01
        detector_params.maxMarkerPerimeterRate = 4.0

        detector = cv2.aruco.ArucoDetector(aruco_dict, detector_params)

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            # Detect ArUco markers
            corners, ids, rejected = detector.detectMarkers(frame)

            # Draw detected markers
            if ids is not None and len(ids) > 0:
                # Draw rectangles around markers
                for i, (corner, marker_id) in enumerate(zip(corners, ids)):
                    corner = corner[0].astype(int)

                    # Draw rectangle around marker
                    cv2.polylines(frame, [corner], True, (0, 255, 0), 3)

                    # Draw center point
                    center_x = int(corner[:, 0].mean())
                    center_y = int(corner[:, 1].mean())
                    cv2.circle(frame, (center_x, center_y), 5, (0, 255, 0), -1)

                    # Draw marker ID
                    cv2.putText(frame, f"ID: {marker_id[0]}",
                               (center_x + 10, center_y - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    # Draw corner points
                    for pt in corner:
                        cv2.circle(frame, tuple(pt), 3, (255, 0, 0), -1)

                # Detection status
                status_text = f"DETECTED: {len(ids)} marker(s)"
                cv2.putText(frame, status_text, (10, frame.shape[0] - 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                # No markers detected
                cv2.putText(frame, "NO MARKERS DETECTED", (10, frame.shape[0] - 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Add camera info overlay
            cv2.putText(frame, f"Camera {self.camera_id}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Resolution: {frame.shape[1]}x{frame.shape[0]}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, "ArUco Dict: DICT_5X5_100", (10, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, "Place marker in view", (10, frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Encode to JPEG
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                with self.lock:
                    self.current_frame = jpeg.tobytes()

    def get_frame(self):
        """Get current frame as JPEG bytes"""
        with self.lock:
            return self.current_frame

    def stop(self):
        """Stop camera capture"""
        self.running = False
        if self.cap:
            self.cap.release()


def main():
    parser = argparse.ArgumentParser(description='RISNet Camera Stream Server')
    parser.add_argument('--port', type=int, default=8080, help='HTTP server port (default: 8080)')
    parser.add_argument('--camera', type=int, default=0, help='Camera ID (default: 0)')
    args = parser.parse_args()

    print("=" * 70)
    print("RISNet Camera Stream Server")
    print("=" * 70)

    # Start camera server
    global camera_server
    camera_server = CameraServer(camera_id=args.camera, fps=30)

    if not camera_server.start():
        return 1

    # Start HTTP server
    server_address = ('', args.port)
    httpd = HTTPServer(server_address, CameraStreamHandler)

    print(f"\n✓ Server running at: http://localhost:{args.port}")
    print(f"✓ Camera: /dev/video{args.camera}")
    print(f"\nOpen http://localhost:{args.port} in your web browser")
    print("Press Ctrl+C to stop\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        camera_server.stop()
        httpd.shutdown()
        print("Done")
        return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
