import cv2
import os
import csv
from ultralytics import YOLO

def run_tracker():
    model_path = "yolo26n-pose_openvino_model"
    if not os.path.exists(model_path):
        print("⏳ Optimizing model for Intel CPU...")
        model = YOLO("yolo26n-pose.pt")
        model.export(format="openvino")

    ov_model = YOLO(model_path)
    video_path = "assets/badminton.mp4"
    cap = cv2.VideoCapture(video_path)
    
    with open('rally_data.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['frame', 'id', 'x', 'y', 'conf']) 

        frame_count = 0
        while cap.isOpened():
            success, frame = cap.read()
            if not success: break
            
            frame_count += 1
            results = ov_model.track(frame, persist=True, device="cpu", tracker="bytetrack.yaml", verbose=False)

            if results[0].boxes.id is not None and results[0].keypoints is not None:
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                keypoints = results[0].keypoints.xy.cpu().numpy() 
                confs = results[0].boxes.conf.cpu().numpy()

                for i, track_id in enumerate(ids):
                    # Keypoint Indices: 15 = Left Ankle, 16 = Right Ankle
                    l_ank = keypoints[i][15]
                    r_ank = keypoints[i][16]

                    # Logic: Use the average of both ankles, or just the one that is visible
                    shoe_x, shoe_y = 0, 0
                    if l_ank[0] > 0 and r_ank[0] > 0:
                        shoe_x, shoe_y = (l_ank[0] + r_ank[0]) / 2, (l_ank[1] + r_ank[1]) / 2
                    elif l_ank[0] > 0:
                        shoe_x, shoe_y = l_ank
                    elif r_ank[0] > 0:
                        shoe_x, shoe_y = r_ank

                    if shoe_x > 0:
                        writer.writerow([frame_count, track_id, round(float(shoe_x), 2), round(float(shoe_y), 2), round(float(confs[i]), 2)])

            cv2.imshow("CourtSense: Ankle Tracking", results[0].plot())
            if cv2.waitKey(1) & 0xFF == ord("q"): break

    cap.release()
    cv2.destroyAllWindows()
    print("✅ Ankle-calibrated data saved to rally_data.csv")

if __name__ == "__main__":
    run_tracker()