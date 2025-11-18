# detect_marker_camera.py
import cv2
import numpy as np
import math

# Camera intrinsics: replace with your calibrated K and dist for better accuracy.
# For quick tests use approximate K with focal ~ image width.
def default_camera_matrix(width, height):
    fx = fy = max(width, height) * 0.9  # rough focal guess
    cx = width / 2.0
    cy = height / 2.0
    K = np.array([[fx, 0, cx],
                  [0, fy, cy],
                  [0,  0,  1]], dtype=np.float64)
    dist = np.zeros((5,))  # assume no distortion for quick test
    return K, dist

MARKER_SIZE_M = 0.10  # meters; set to printed/onscreen marker approximate physical size seen by camera

def main(cam_index=0):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print("ERROR: cannot open camera")
        return

    ret, frame = cap.read()
    if not ret:
        print("ERROR: cannot read from camera")
        return

    h, w = frame.shape[:2]
    K, dist = default_camera_matrix(w, h)

    try:
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100)
        parameters = cv2.aruco.DetectorParameters()
    except AttributeError:
        aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_5X5_100)
        parameters = cv2.aruco.DetectorParameters_create()

    print("Press 'q' to quit. Point camera at marker (prefer printed or fullscreen image).")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        try:
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
            corners, ids, rejected = detector.detectMarkers(gray)
        except AttributeError:
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

        if ids is not None:
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, MARKER_SIZE_M, K, dist)
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            for i, marker_id in enumerate(ids.flatten()):
                rvec = rvecs[i]
                tvec = tvecs[i][0]  # (x,y,z) in camera frame (meters)

                # Draw axis
                try:
                    cv2.drawFrameAxes(frame, K, dist, rvec, tvec, MARKER_SIZE_M * 0.5)
                except AttributeError:
                    cv2.aruco.drawAxis(frame, K, dist, rvec, tvec, MARKER_SIZE_M * 0.5)

                x, y, z = tvec
                dist_cam = math.sqrt(x*x + y*y + z*z)

                text = f"ID:{marker_id} x:{x:.2f} y:{y:.2f} z:{z:.2f} m d:{dist_cam:.2f}m"
                cv2.putText(frame, text, (10, 30 + 30*i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

        else:
            cv2.putText(frame, "NO MARKERS DETECTED - place marker fullscreen or print it", (10,30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

        cv2.imshow("ArUco Detector", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
