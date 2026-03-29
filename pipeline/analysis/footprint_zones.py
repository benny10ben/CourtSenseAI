import cv2
import pandas as pd
import argparse
import json
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
ROOT              = Path(__file__).resolve().parents[2]
FRAME_CAL         = 1

ZONE_LABELS  = ['FL', 'FR', 'BL', 'BR']
ZONE_NAMES   = {'FL': 'Front-Left', 'FR': 'Front-Right', 'BL': 'Back-Left', 'BR': 'Back-Right'}
KEY_TO_LABEL = {ord('1'): 'FL', ord('2'): 'FR', ord('3'): 'BL', ord('4'): 'BR'}
# ─────────────────────────────────────────────────────────────────────────────

click_pts = []

def mouse_callback(event, x, y, flags, param):
    global click_pts
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(click_pts) < 2:
            click_pts.append((x, y))

def calibrate_zones(video_file, calibrate_frame):
    global click_pts
    cap = cv2.VideoCapture(str(video_file))
    cap.set(cv2.CAP_PROP_POS_FRAMES, calibrate_frame)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"❌ Error: Could not read video frame at index {calibrate_frame}")
        return {}

    window_name = "Draw Player Footprint Zones"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)
    cv2.setMouseCallback(window_name, mouse_callback)

    boxes       = {'P1': {}, 'P2': {}}
    current_box = None
    state       = 'click1'
    pt1         = None

    all_needed = [('P1', z) for z in ZONE_LABELS] + [('P2', z) for z in ZONE_LABELS]
    saved_log  = []

    def get_remaining():
        return [f"{p}-{z}" for p, z in all_needed if z not in boxes[p]]

    while True:
        display = frame.copy()

        for player, zones in boxes.items():
            color = (100, 100, 255) if player == 'P1' else (50, 200, 255)
            for label, (x1, y1, x2, y2) in zones.items():
                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                cv2.putText(display, f"{player}-{label}", (x1 + 4, y1 + 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        needed = get_remaining()
        if not needed:
            cv2.putText(display, "All 8 zones done! Press ENTER to save & analyze.",
                        (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            cv2.imshow(window_name, display)
            if (cv2.waitKey(20) & 0xFF) == 13:
                break
            continue

        player = needed[0].split('-')[0]

        if state == 'click2' and pt1 and click_pts:
            cv2.circle(display, pt1, 6, (0, 255, 0), -1)
        if state == 'label' and current_box:
            cv2.rectangle(display, (current_box[0], current_box[1]),
                          (current_box[2], current_box[3]), (0, 255, 255), 2)

        h = display.shape[0]
        cv2.rectangle(display, (0, h - 80), (1000, h), (0, 0, 0), -1)
        msg = (f"[{player}] Click TOP-LEFT" if state == 'click1'
               else f"[{player}] Click BOTTOM-RIGHT" if state == 'click2'
               else "Press: 1=FL, 2=FR, 3=BL, 4=BR")
        cv2.putText(display, msg, (10, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display, f"Need: {needed[:3]}... | C=Undo | ENTER=Done",
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

        cv2.imshow(window_name, display)
        key = cv2.waitKey(20) & 0xFF

        if state == 'click1' and len(click_pts) == 1:
            pt1       = click_pts[0]
            click_pts = []
            state     = 'click2'
        elif state == 'click2' and len(click_pts) == 1:
            pt2         = click_pts[0]
            click_pts   = []
            current_box = (min(pt1[0], pt2[0]), min(pt1[1], pt2[1]),
                           max(pt1[0], pt2[0]), max(pt1[1], pt2[1]))
            state       = 'label'
        elif state == 'label' and key in KEY_TO_LABEL:
            lbl = KEY_TO_LABEL[key]
            if lbl not in boxes[player]:
                boxes[player][lbl] = current_box
                saved_log.append((player, lbl))
                current_box = None
                pt1         = None
                state       = 'click1'

        if key == ord('c') and saved_log:
            last_p, last_l = saved_log.pop()
            del boxes[last_p][last_l]
            current_box = None
            pt1         = None
            click_pts   = []
            state       = 'click1'

    cv2.destroyAllWindows()
    return boxes

def analyze_footprint(csv_file, boxes):
    if not Path(csv_file).exists():
        print(f"❌ Error: {csv_file} not found.")
        return {}

    df     = pd.read_csv(csv_file)
    counts = {'P1': {z: 0 for z in ZONE_LABELS}, 'P2': {z: 0 for z in ZONE_LABELS}}

    for _, row in df.iterrows():
        if pd.isna(row['Player_ID']):
            continue
        pid = f"P{int(row['Player_ID'])}"
        if pid not in ['P1', 'P2']:
            continue

        x_col = 'P1_KP16_X' if pid == 'P1' else 'P2_KP16_X'
        y_col = 'P1_KP16_Y' if pid == 'P1' else 'P2_KP16_Y'
        
        if x_col not in df.columns:
            x_col, y_col = 'KP16_X', 'KP16_Y'

        if x_col not in df.columns:
            continue

        ax, ay = row[x_col], row[y_col]
        if ax == 0 and ay == 0:
            continue

        for label, (x1, y1, x2, y2) in boxes[pid].items():
            if x1 <= ax <= x2 and y1 <= ay <= y2:
                counts[pid][label] += 1
                break

    return counts

def export_zones_to_csv(boxes, filename):
    with open(filename, 'w') as f:
        f.write("Player,Zone,X1,Y1,X2,Y2\n")
        for player, zones in boxes.items():
            pid = 1 if player == 'P1' else 2
            for label, (x1, y1, x2, y2) in zones.items():
                f.write(f"{pid},{label},{x1},{y1},{x2},{y2}\n")
    print(f"✅ Zone coordinates saved to {filename}")

def export_footprint_to_csv(counts, filename):
    rows = []
    for player, zones in counts.items():
        pid = 1 if player == 'P1' else 2
        for zone_label, frame_count in zones.items():
            rows.append({
                'Player'     : pid,
                'Zone'       : ZONE_NAMES[zone_label],
                'Zone_Label' : zone_label,
                'Frame_Count': frame_count,
            })
    if rows:
        pd.DataFrame(rows).to_csv(filename, index=False)
        print(f"✅ Zone footprint saved to {filename}")
    else:
        print("⚠️ No footprint data generated to save.")

def main():
    print("🏸 CourtSenseAI - Interactive Footprint Analyzer")
    print("================================================")

    parser = argparse.ArgumentParser(description="Analyze player footprint zones.")
    parser.add_argument("--coords", type=str, help="Path to JSON file containing court coordinates", default=None)
    parser.add_argument("--output-dir", type=str, required=True, help="Session output directory")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    POSE_CSV          = out_dir / 'players_pose_clean.csv'
    OUT_ZONES_CSV     = out_dir / 'court_zones.csv'
    OUT_FOOTPRINT_CSV = out_dir / 'zone_footprint.csv'

    session_video = out_dir.parent / 'assets' / 'badminton.mp4'
    VIDEO_FILE = session_video if session_video.exists() else ROOT / 'assets' / 'badminton.mp4'

    if args.coords:
        print(f"Headless mode activated. Reading zones from {args.coords}...")
        with open(args.coords, 'r') as f:
            payload = json.load(f)

        json_to_internal = {
            'front_left': 'FL', 'front_right': 'FR',
            'back_left': 'BL', 'back_right': 'BR'
        }

        boxes = {'P1': {}, 'P2': {}}
        
        if 'p1_zones' in payload:
            for j_key, j_val in payload['p1_zones'].items():
                if j_key in json_to_internal:
                    boxes['P1'][json_to_internal[j_key]] = tuple(j_val)
                    
        if 'p2_zones' in payload:
            for j_key, j_val in payload['p2_zones'].items():
                if j_key in json_to_internal:
                    boxes['P2'][json_to_internal[j_key]] = tuple(j_val)

        print("Zone boxes loaded from JSON.")
    else:
        boxes = calibrate_zones(VIDEO_FILE, FRAME_CAL)
        if not boxes or not boxes['P1']:
            print("❌ Calibration cancelled or failed.")
            return

    export_zones_to_csv(boxes, OUT_ZONES_CSV)

    print("\nProcessing player trajectories...")
    counts = analyze_footprint(POSE_CSV, boxes)

    export_footprint_to_csv(counts, OUT_FOOTPRINT_CSV)

    print("\n==================================================")
    print("📊 TACTICAL FOOTPRINT REPORT (% of Time Spent)")
    print("==================================================")

    for player in ['P1', 'P2']:
        total = sum(counts[player].values())
        if total == 0:
            total = 1

        pcts  = {z: (counts[player][z] / total) * 100 for z in ZONE_LABELS}
        title = "PLAYER 1 (Far Court)" if player == 'P1' else "PLAYER 2 (Near Court)"

        print(f"\n🏸 {title}  [Frames Tracked: {total}]")
        print("┌───────────────┬───────────────┐")

        if player == 'P1':
            print(f"│  BL: {pcts['BL']:>5.1f}%  │  BR: {pcts['BR']:>5.1f}%  │")
            print("├───────────────┼───────────────┤")
            print(f"│  FL: {pcts['FL']:>5.1f}%  │  FR: {pcts['FR']:>5.1f}%  │")
        else:
            print(f"│  FL: {pcts['FL']:>5.1f}%  │  FR: {pcts['FR']:>5.1f}%  │")
            print("├───────────────┼───────────────┤")
            print(f"│  BL: {pcts['BL']:>5.1f}%  │  BR: {pcts['BR']:>5.1f}%  │")

        print("└───────────────┴───────────────┘")

        if total > 10:
            fav_zone = max(counts[player], key=counts[player].get)
            print(f"   ↳ Positional Bias: Player favors {ZONE_NAMES[fav_zone]}.")

    print("\n==================================================\n")

if __name__ == '__main__':
    main()