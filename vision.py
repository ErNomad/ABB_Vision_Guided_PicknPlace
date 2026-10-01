import numpy as np
from shapely.geometry import Polygon
import math
import cv2
import cv2.aruco as aruco
from ultralytics import YOLO
from pypylon import pylon

color_ranges = {
    "Black": ([0, 0, 0], [180, 255, 38]),
    "Blue": ([94, 80, 2], [135, 255, 255]),
    "Green": ([30, 20, 20], [80, 255, 70]),
    "Red": ([0, 40, 30], [10, 255, 255])
}

class Vision:
    def __init__(self, model_path, marker_size=100):
        self.model_path = model_path
        self.marker_size = marker_size
        self.color_ranges = color_ranges.copy()
    
    def _simplify_to_n_vertices(self, poly, n=5):
        polygon = Polygon(poly)
        tol = 1.0
        simplified = polygon.simplify(tol, preserve_topology=True)
        while len(simplified.exterior.coords) - 1 > n and tol < 50:
            tol *= 1.2
            simplified = polygon.simplify(tol, preserve_topology=True)
        coords = list(simplified.exterior.coords)[:-1]  # remove duplicate last point
        if len(coords) > n:
            coords = coords[:n]
        return coords

    def _project_to_frame(self, point, origin, x_axis, y_axis, scale):
        vec = np.array(point) - np.array(origin)
        x_pix = np.dot(vec, x_axis)
        y_pix = np.dot(vec, y_axis)
        return x_pix * scale, y_pix * scale  # in mm
    

    # --- Helper: compute minimum-area rectangle ---
    def _calc_sqr_cir_params(self, poly, origin, x_axis, y_axis, scale):
        #import cv2
        
        pts = np.asarray(poly, dtype=np.float32)
        
        if len(pts) < 3:
            return None, 0.0, (0, 0), (0, 0)

        rect = cv2.minAreaRect(pts)
        (cx, cy), (w, h), _ = rect

        if w * h * scale * scale < 1250:
            return None, 0.0, (0, 0), (0, 0)
        
        box = cv2.boxPoints(rect)
        
        verts_mm = []
        for (vx, vy) in box:
            x_mm, y_mm = self._project_to_frame((vx, vy), origin, x_axis, y_axis, scale)
            verts_mm.append([x_mm, y_mm])
        verts_mm = np.array(verts_mm)
        
        cx_mm, cy_mm = self._project_to_frame((cx, cy), origin, x_axis, y_axis, scale)
        
        x_mm_vals = verts_mm[:, 0]    # distance of vertices to y-axis
        idx_near_y = int(np.argmin(np.abs(x_mm_vals))) # index of closest vertex to y-axis
        closest_to_y_mm = verts_mm[idx_near_y] # closest vertex to y-axis
        
        # vector from centroid to the closest-to-y-axis vertex (in mm frame)
        v = closest_to_y_mm - np.array([cx_mm, cy_mm], dtype=float)
        dx, dy = float(v[0]), float(v[1])

        # signed angle relative to +x axis of the workobject (CCW positive)
        angle_deg = np.degrees(np.arctan2(dy, dx))  # in (-180, 180]
        
        angle_deg = (180 - angle_deg - 45) if angle_deg >= 0 else (-180 - angle_deg + 45)

        return rect, angle_deg, (cx, cy), (cx_mm, cy_mm)

    def _compute_star_params(self, poly, origin, x_axis, y_axis, scale):
        # Step 1: simplify to pentagon (in pixel coordinates)
        verts = self._simplify_to_n_vertices(poly, n=5)
        if len(verts) < 2:
            return 0.0, None, None, None

        verts = np.array(verts)

        # --- Pixel centroid (for OpenCV drawing) ---
        px_cx, px_cy = np.mean(verts[:, 0]), np.mean(verts[:, 1])

        # Step 2: project vertices into workobject frame (mm)
        verts_mm = []
        for (vx, vy) in verts:
            x_mm, y_mm = self._project_to_frame((vx, vy), origin, x_axis, y_axis, scale)
            verts_mm.append([x_mm, y_mm])
        verts_mm = np.array(verts_mm)

        # --- Workobject centroid (for robot use) ---
        mm_cx, mm_cy = np.mean(verts_mm[:, 0]), np.mean(verts_mm[:, 1])
        
        x_mm_vals = verts_mm[:, 0]    # distance of vertices to y-axis
        idx_near_y = int(np.argmin(np.abs(x_mm_vals))) # index of closest vertex to y-axis
        closest_to_y_mm = verts_mm[idx_near_y] # closest vertex to y-axis
        
        # vector from centroid to the closest-to-y-axis vertex (in mm frame)
        v = closest_to_y_mm - np.array([mm_cx, mm_cy], dtype=float)
        dx, dy = float(v[0]), float(v[1])

        # signed angle relative to +x axis of the workobject (CCW positive)
        angle_deg = np.degrees(np.arctan2(dy, dx))  # in (-180, 180]
            
        angle_deg = (180 - angle_deg) if angle_deg >= 0 else (-180 - angle_deg)

        return (
            angle_deg if angle_deg is not None else 0.0,  # orientation angle
            (px_cx, px_cy),  # pixel centroid
            (mm_cx, mm_cy),  # mm centroid
            verts            # pentagon vertices in pixels
        )

    def _object_color_handler(self, HSV_F, color_name, origin, x_axis, y_axis, scale, x2, y2):
        #import cv2
        color_centers = []

        lower, upper = self.color_ranges[color_name]
        lower_bound = np.array(lower, dtype="uint8")
        upper_bound = np.array(upper, dtype="uint8")
        mask = cv2.inRange(HSV_F, lower_bound, upper_bound)
        cv2.imshow("Detection with WorkObject", mask)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            if cv2.contourArea(contour) > 100:
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    ccX = int(M["m10"] / M["m00"])
                    ccY = int(M["m01"] / M["m00"])

                    ccX_mm, ccY_mm = self._project_to_frame((ccX, ccY), origin, x_axis, y_axis, scale)
                    color_centers.append((ccX_mm, ccY_mm))

        n = len(color_centers)
        for i in range(n):
            x1, y1 = color_centers[i]

            distance = math.hypot(x2 - x1, y2 - y1)
            if distance <= 15:
                return True
    
    def set_color_range(self, color_name, lower, upper):
        self.color_ranges[color_name] = (lower, upper)

    def vision_process(self, command_queue, result_queue):
        #import cv2
        #import cv2.aruco as aruco
        #from ultralytics import YOLO
        #from pypylon import pylon
        
        model = YOLO(self.model_path)
        
        # --- Open Basler camera ---
        camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        camera.Open()
        camera.Width.SetValue(1820)
        camera.Height.SetValue(1320)
        camera.OffsetX.SetValue(0)
        camera.OffsetY.SetValue(0)
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        dictionary = aruco.getPredefinedDictionary(aruco.DICT_5X5_100)
        parameters = aruco.DetectorParameters()
        detector = aruco.ArucoDetector(dictionary, parameters)
        
        cv2.namedWindow("Detection with WorkObject", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Detection with WorkObject", 1820, 1320)

        while camera.IsGrabbing():
            grabResult = camera.RetrieveResult(500, pylon.TimeoutHandling_ThrowException)
            if grabResult.GrabSucceeded():
                image = converter.Convert(grabResult)
                frame = image.GetArray()   # <-- OpenCV frame

            grabResult.Release()  # <--- this is critical

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            corners, ids, rejected = detector.detectMarkers(gray)

            #lower, upper = self.color_ranges["Green"]
            #lower_bound = np.array(lower, dtype="uint8")
            #upper_bound = np.array(upper, dtype="uint8")
            #mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)
            #cv2.imshow("mask", mask)

            if ids is not None:
                # Use first marker
                pts = corners[0][0]
                top_left, top_right, bottom_right, bottom_left = pts

                # Draw marker
                aruco.drawDetectedMarkers(frame, corners, ids)

                # Work object axes
                y_axis = (top_right - top_left)
                y_axis = y_axis / np.linalg.norm(y_axis)
                x_axis = (bottom_left - top_left)
                x_axis = x_axis / np.linalg.norm(x_axis)
                origin = top_left

                marker_width_pix = np.linalg.norm(top_right - top_left)
                scale = self.marker_size / marker_width_pix

                # --- Run YOLO detection ---
                results = model.predict(frame, task='segment', imgsz=640, conf=0.25, verbose=False)

                if results and results[0].boxes is not None and len(results[0].boxes) > 0:
                    #pass
                    print(results[0].speed['inference'])

                requested_object = None
                requested_color = None
                requested_shape = None
                if not command_queue.empty():
                    requested_object = command_queue.get()
                    requested_color, requested_shape = requested_object.split()

                found = False

                for res in results:
                    if res.masks is not None:
                        for i, poly in enumerate(res.masks.xy):
                            cls_id = int(res.boxes.cls[i])
                            label = model.names[cls_id]

                            poly_np = np.array(poly)

                            if label == "Star":
                                ang, (cx, cy), (x_mm, y_mm), verts = self._compute_star_params(poly, origin, x_axis, y_axis, scale)
                                cv2.circle(frame, (int(cx), int(cy)), 5, (255, 255, 255), -1)
                                cv2.putText(frame, f"{label} ({x_mm:.1f}, {y_mm:.1f} mm, {ang:.1f}deg)",
                                    (int(cx)+10, int(cy)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                                if len(verts) >= 3:
                                    pts = np.array(verts, np.int32).reshape((-1,1,2))
                                    cv2.polylines(frame, [pts], isClosed=True, color=(255, 255, 255), thickness=2)

                            elif label in ["Square", "Circle"]:
                                rect, ang, (cx, cy), (x_mm, y_mm) = self._calc_sqr_cir_params(poly, origin, x_axis, y_axis, scale)
                                cv2.circle(frame, (int(cx), int(cy)), 5, (255, 255, 255), -1)
                                cv2.putText(frame, f"{label} ({x_mm:.1f}, {y_mm:.1f} mm)",
                                    (int(cx)+10, int(cy)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                                if rect is not None:
                                    box = cv2.boxPoints(rect)
                                    box = box.astype(int).reshape((-1,1,2))
                                    cv2.polylines(frame, [box], isClosed=True, color=(255, 255, 255), thickness=2)
                                    x_txt, y_txt = box[0][0]
                                    cv2.putText(frame, f"{ang:.1f}deg", (int(x_txt), int(y_txt)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                            else:
                                pts = poly_np.astype(int).reshape((-1,1,2))
                                cv2.polylines(frame, [pts], isClosed=True, color=(255, 255, 255), thickness=2)

                            if label == requested_shape:
                                color_bool = self._object_color_handler(hsv_frame, requested_color, origin, x_axis, y_axis, scale, x_mm, y_mm)
                                if color_bool:
                                    result_queue.put(f"[{x_mm:.1f}, {y_mm:.1f}, -5, {ang:.1f}]")
                                    found = True
                                    break
                        
                        if found:
                            break
                
                if requested_object != None and not found:
                    result_queue.put("Not found!")


            cv2.imshow("Detection with WorkObject", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        camera.StopGrabbing()
        camera.Close()
        cv2.destroyAllWindows()