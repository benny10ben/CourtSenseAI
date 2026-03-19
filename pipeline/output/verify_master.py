import cv2
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[2]
CSV_FILE   = ROOT / 'data' / 'output' / 'rally_master.csv'
VIDEO_FILE = ROOT / 'assets' / 'badminton.mp4'
OUT_FILE   = ROOT / 'data' / 'output' / 'master_verification.mp4'

# COCO Skeleton Pairs
SKELETON = [
    (15, 13), (13, 11), (16, 14), (14, 12), (11, 12), (5, 11), (6, 12), (5, 6),
    (5, 7), (6, 8), (7, 9), (8, 10), (1, 2), (0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 6)
]
# ─────────────────────────────────────────────────────────────────────────────


def draw_player(frame, row, prefix, color):
    # 1. Draw Skeleton
    for start_node, end_node in SKELETON:
        x1 = int(row[f'{prefix}KP{start_node}_X'])
        y1 = int(row[f'{prefix}KP{start_node}_Y'])
        x2 = int(row[f'{prefix}KP{end_node}_X'])
        y2 = int(row[f'{prefix}KP{end_node}_Y'])
        if x1 > 0 and x2 > 0:
            cv2.line(frame, (x1, y1), (x2, y2), color, 2)

    # 2. Draw Joints
    for i in range(17):
        x, y = int(row[f'{prefix}KP{i}_X']), int(row[f'{prefix}KP{i}_Y'])
        if x > 0:
            cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)

    # 3. Draw Bounding Box & Label
    bx1, by1 = int(row[f'{prefix}Box_X1']), int(row[f'{prefix}Box_Y1'])
    bx2, by2 = int(row[f'{prefix}Box_X2']), int(row[f'{prefix}Box_Y2'])
    if bx1 > 0:
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 2)
        cv2.putText(frame, prefix.strip('_'), (bx1, by1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def main():
    print(f"🎬 Auditing Master Data from {CSV_FILE}...")
    df = pd.read_csv(CSV_FILE)

    cap     = cv2.VideoCapture(VIDEO_FILE)
    fps     = cap.get(cv2.CAP_PROP_FPS)
    w, h    = int(cap.get(3)), int(cap.get(4))
    total   = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    out = cv2.VideoWriter(OUT_FILE, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_data = df[df['Frame'] == frame_idx]

        if not frame_data.empty:
            row = frame_data.iloc[0]

            # Draw P1 (Yellow) and P2 (Cyan)
            draw_player(frame, row, 'P1_', (0, 255, 255))
            draw_player(frame, row, 'P2_', (255, 255, 0))

            # Draw the Ball
            if row['Ball_Vis'] == 1:
                cv2.circle(frame, (int(row['Ball_X']), int(row['Ball_Y'])), 8, (0, 0, 255), -1)
                cv2.circle(frame, (int(row['Ball_X']), int(row['Ball_Y'])), 8, (255, 255, 255), 2)

        out.write(frame)
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"  Frame {frame_idx}/{total}...")

    cap.release()
    out.release()
    print(f"✅ Audit complete! Saved to: {OUT_FILE}")


if __name__ == '__main__':
    main()