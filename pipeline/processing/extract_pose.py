import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO

# ── Config ────────────────────────────────────────────────────────────────────
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
MODEL_PATH  = ROOT / 'models' / 'yolo26n-pose.pt'
VIDEO_FILE  = ROOT / 'assets' / 'badminton.mp4'
OUT_CSV     = ROOT / 'data' / 'output' / 'players_pose_full.csv'
START_FRAME = 1
# ─────────────────────────────────────────────────────────────────────────────

roi_points = []


def mouse_callback(event, x, y, flags, param):
    global roi_points
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points.append((x, y))
        print(f"Point captured: ({x}, {y})")


def calibrate_court(cap):
    global roi_points

    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {VIDEO_FILE}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video opened. Total frames: {total}")

    cap.set(cv2.CAP_PROP_POS_FRAMES, START_FRAME)
    ret, frame = cap.read()
    if not ret:
        raise ValueError(f"Could not read frame {START_FRAME}. Video only has {total} frames.")

    window_name = "Calibrate Court (Resizable)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)
    cv2.setMouseCallback(window_name, mouse_callback)

    print("\n" + "=" * 50)
    print("INTERACTIVE COURT CALIBRATION")
    print("1. Click the 4 corners of the playable floor.")
    print("2. Press ENTER to confirm.")
    print("3. Press 'c' to clear and re-click.")
    print("=" * 50 + "\n")

    while True:
        display = frame.copy()

        for i, pt in enumerate(roi_points):
            cv2.circle(display, pt, 8, (0, 0, 255), -1)
            if i > 0:
                cv2.line(display, roi_points[i - 1], pt, (0, 255, 0), 3)

        if len(roi_points) == 4:
            cv2.line(display, roi_points[3], roi_points[0], (0, 255, 0), 3)
            cv2.putText(display, "Press ENTER to confirm", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow(window_name, display)
        key = cv2.waitKey(1) & 0xFF

        if key == 13 and len(roi_points) >= 4:  # ENTER
            break
        elif key == ord('c'):
            roi_points = []
            print("Cleared. Click again.")

    cv2.destroyAllWindows()
    return np.array(roi_points, np.int32)


def main():
    print("Loading YOLO-Pose model...")
    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(VIDEO_FILE)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {VIDEO_FILE}")

    # Step 1 — interactive court calibration
    court_polygon = calibrate_court(cap)
    print("Court geofence locked. Starting player tracking...")

    # Step 2 — reset and process from frame 0
    pose_data = []
    frame_idx = 0
    cap.release()  # release before model.track() opens the video itself

    results = model.track(
        source=VIDEO_FILE,
        persist=True,
        tracker="bytetrack.yaml",
        stream=True,
        device='cpu',
        imgsz=1280,   # 640 is faster on CPU; use 1280 if far player is missed
        verbose=False
    )

    for r in results:
        if r.boxes.id is not None:
            boxes     = r.boxes.xyxy.cpu().numpy()
            track_ids = r.boxes.id.cpu().numpy().astype(int)
            keypoints = r.keypoints.xy.cpu().numpy()

            for i in range(len(boxes)):
                x1, y1, x2, y2 = boxes[i]

                # Geofence check — feet must be inside the 4 clicked corners
                foot_x    = int((x1 + x2) / 2)
                foot_y    = int(y2)
                is_inside = cv2.pointPolygonTest(court_polygon, (foot_x, foot_y), False)
                if is_inside < 0:
                    continue

                kpts = keypoints[i]
                row  = {
                    'Frame':     frame_idx,
                    'Player_ID': track_ids[i],
                    'Box_X1':    int(x1),
                    'Box_Y1':    int(y1),
                    'Box_X2':    int(x2),
                    'Box_Y2':    int(y2),
                }

                # All 17 COCO keypoints
                for kp_idx in range(17):
                    if len(kpts) > kp_idx:
                        row[f'KP{kp_idx}_X'] = int(kpts[kp_idx][0])
                        row[f'KP{kp_idx}_Y'] = int(kpts[kp_idx][1])
                    else:
                        row[f'KP{kp_idx}_X'] = 0
                        row[f'KP{kp_idx}_Y'] = 0

                pose_data.append(row)

        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"  Processed {frame_idx} frames...")

    df = pd.DataFrame(pose_data)
    df.to_csv(OUT_CSV, index=False)
    print(f"\n✅ Done! {len(df)} detections saved to: {OUT_CSV}")
    print(f"   Unique Player IDs found: {sorted(df['Player_ID'].unique().tolist())}")


if __name__ == '__main__':
    main()