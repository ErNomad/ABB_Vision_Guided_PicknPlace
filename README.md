# Robot Computer Vision

This project combines camera-based object detection with an ABB robot pick-and-place program. The Python application uses a Basler camera, an ArUco marker to define a work-object coordinate frame, a YOLO segmentation model to locate shapes, and HSV color masks to select the requested object. It sends the selected object's position and angle to the robot over TCP.

The supported shape labels are `Circle`, `Square`, and `Star`. The color-selection code is configured for `Black`, `Blue`, `Green`, and `Red`.

## Project files

- `coord.py` starts the Python communication and vision processes.
- `comm.py` runs the TCP server that exchanges requests and results with the robot.
- `vision.py` handles Basler camera capture, ArUco detection, YOLO segmentation, color filtering, and coordinate conversion.
- `best.pt` contains the YOLO model weights used by the vision process.
- `MainModule.mod` contains the ABB RAPID pick-and-place program.
- `ServerCommuncatio.sys` contains ABB RAPID TCP communication routines.
- `color_test.py` is a camera utility for interactively tuning HSV thresholds.
- `requirements.txt` lists the Python package dependencies.

## Requirements

- Python and the packages listed in `requirements.txt`
- A Basler camera with the Basler Pylon software/runtime installed
- An ABB robot/controller configured to run the provided RAPID modules
- A network connection between the computer and robot, with TCP port `5000` available
- An ArUco marker from the `DICT_5X5_100` dictionary, placed in view of the camera

The vision code assumes the marker is `100 mm` wide by default. Use the actual printed marker width when configuring the vision process.

## Setup

1. Clone or copy this project to the computer connected to the camera.
2. Install the Python dependencies:

   ```powershell
   cd C:\path\to\Robot_ComputerVision
   python -m pip install -r requirements.txt
   ```

3. Open `coord.py` and update the `Vision` model path to the location of this project's `best.pt` file. The checked-in value points to a machine-specific `H:` drive path.
4. Configure the TCP server address in `coord.py`'s `Communication` instance. It must be an IP address assigned to the computer and reachable from the robot.
5. In `MainModule.mod`, set the address passed to `SocketConnect` to the same computer IP. Keep the port at `5000` on both sides, and allow that port through the computer's firewall if required.
6. Confirm that camera exposure, marker placement, robot work objects, tool data, pick/place targets, and HSV thresholds are calibrated for your physical setup. The robot coordinates and targets in the RAPID files are installation-specific.

## Run

1. Start the Python application from the project directory:

   ```powershell
   python coord.py
   ```

   The process opens the TCP server and starts camera-based detection. A live OpenCV window displays detections; press `q` in that window to close the vision loop, then stop the remaining server process from the terminal.

2. Load `ServerCommuncatio.sys` and `MainModule.mod` into the ABB controller and run the robot program. The robot connects to the Python computer and prompts the operator to choose a shape and color.
3. Keep the ArUco marker and the requested object visible to the camera. When a matching object is detected, its position is sent to the robot for the programmed pick-and-place action.

Start the Python server before starting the RAPID program so the robot can connect. The marker must be detected before a request can be processed; without it, the robot request waits for a result. If the marker is visible but the requested object is not found, the Python application responds with `Not found!`.

## Communication and coordinates

The robot requests an object by sending a color and shape separated by a space, for example `Blue Circle`. The Python application responds with either:

- A coordinate array in the form `[x, y, -5, angle]`, where `x` and `y` are in millimetres relative to the detected ArUco marker's work-object frame and `angle` is in degrees.
- `Not found!` when no matching object is detected.

The robot sends `PickNPlace done!` after completing its cycle and requests another object. The work-object axes and marker-to-millimetre scale are derived from the detected marker; the marker width and robot work-object calibration must therefore agree.

## HSV color tuning

Run `python color_test.py` on a computer connected to the Basler camera to open trackbars for adjusting lower and upper HSV bounds. Use the resulting thresholds to update the color ranges in `coord.py`. The active thresholds in `coord.py` override the defaults in `vision.py`.

## Safety

This software can command physical robot motion. Before operation, validate the coordinate frame, marker size, tool/work-object data, reachability, and pick/place positions with the robot in a safe setup and at an appropriate reduced speed. Keep the robot cell clear and follow the controller and facility safety procedures. The supplied RAPID targets and motion settings are examples for a particular installation, not universal safe values.