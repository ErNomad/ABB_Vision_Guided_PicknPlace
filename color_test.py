import cv2
import numpy as np
from pypylon import pylon

def nothing(x):
    pass

# Connect to Basler camera
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
camera.Open()
camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

# Create OpenCV windows
cv2.namedWindow("Trackbars", cv2.WINDOW_NORMAL)
cv2.namedWindow("Masked Output", cv2.WINDOW_NORMAL)
cv2.namedWindow("Original", cv2.WINDOW_NORMAL)

# Create trackbars for HSV lower and upper bounds
cv2.createTrackbar("L - H", "Trackbars", 0, 179, nothing)
cv2.createTrackbar("L - S", "Trackbars", 0, 255, nothing)
cv2.createTrackbar("L - V", "Trackbars", 0, 255, nothing)
cv2.createTrackbar("U - H", "Trackbars", 179, 179, nothing)
cv2.createTrackbar("U - S", "Trackbars", 255, 255, nothing)
cv2.createTrackbar("U - V", "Trackbars", 255, 255, nothing)

try:
    while camera.IsGrabbing():
        grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grab_result.GrabSucceeded():
            # Convert to OpenCV image
            img = grab_result.Array
            frame = cv2.cvtColor(img, cv2.COLOR_BAYER_BG2BGR)  # Change based on camera's pixel format

            # Resize for display (optional)
            frame_resized = cv2.resize(frame, (640, 480))

            # Convert to HSV
            hsv = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2HSV)

            # Get current positions of trackbars
            l_h = cv2.getTrackbarPos("L - H", "Trackbars")
            l_s = cv2.getTrackbarPos("L - S", "Trackbars")
            l_v = cv2.getTrackbarPos("L - V", "Trackbars")
            u_h = cv2.getTrackbarPos("U - H", "Trackbars")
            u_s = cv2.getTrackbarPos("U - S", "Trackbars")
            u_v = cv2.getTrackbarPos("U - V", "Trackbars")

            lower_bound = np.array([l_h, l_s, l_v])
            upper_bound = np.array([u_h, u_s, u_v])

            # Create mask and apply it
            mask = cv2.inRange(hsv, lower_bound, upper_bound)
            result = cv2.bitwise_and(frame_resized, frame_resized, mask=mask)

            # Show windows
            cv2.imshow("Original", frame_resized)
            cv2.imshow("Masked Output", result)

            key = cv2.waitKey(1)
            if key == 27:  # ESC key to break
                break

        grab_result.Release()

finally:
    # Cleanup
    camera.StopGrabbing()
    camera.Close()
    cv2.destroyAllWindows()
