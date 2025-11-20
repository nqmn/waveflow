import cv2

def list_available_cameras():
    """
    Tests camera indices to find available cameras and returns a list of working camera indices.
    """
    available_cameras = []
    # Test up to a reasonable number of potential camera indices
    # You might need to adjust this range depending on your system and the number of cameras
    for i in range(10): 
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release() # Release the camera after checking
    return available_cameras

if __name__ == "__main__":
    cameras = list_available_cameras()
    if cameras:
        print("Available cameras found at indices:")
        for cam_index in cameras:
            print(f"- Camera {cam_index}")
    else:
        print("No cameras found.")