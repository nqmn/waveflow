# generate_marker.py
import cv2
import numpy as np
import argparse
import os

def make_marker(dict_name, marker_id, size_px, out_path, show_fullscreen=False):
    try:
        aruco_dict = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dict_name))
        marker = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_px)
    except AttributeError:
        aruco_dict = cv2.aruco.Dictionary_get(getattr(cv2.aruco, dict_name))
        marker = cv2.aruco.drawMarker(aruco_dict, marker_id, size_px)
    cv2.imwrite(out_path, marker)
    print(f"Saved: {out_path} ({size_px}px)")

    if show_fullscreen:
        win = "ARUCO_MARKER_FULLSCREEN"
        cv2.namedWindow(win, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        # show image centered on screen
        cv2.imshow(win, marker)
        print("Press any key to exit fullscreen display.")
        cv2.waitKey(0)
        cv2.destroyWindow(win)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, default=0, help="Marker ID (0..99 for DICT_5X5_100)")
    parser.add_argument("--size", type=int, default=1200, help="Pixel size of output marker (square)")
    parser.add_argument("--out", type=str, default="aruco_5x5_id0.png")
    parser.add_argument("--show", action="store_true", help="Show fullscreen after creating")
    args = parser.parse_args()

    # Use dictionary DICT_5X5_100
    make_marker("DICT_5X5_100", args.id, args.size, args.out, args.show)
