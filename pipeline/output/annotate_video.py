"""
annotate_video.py
-----------------
Draws the tracked shuttlecock position on top of the original video.
Output: a new MP4 with a red dot (current ball) and yellow trail (last N frames).

Usage:
    python3 annotate_video.py
"""

import cv2
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
from pathlib import Path

ROOT         = Path(__file__).resolve().parents[2]
CSV_FILE     = ROOT / 'TrackNetV3' / 'output' / 'badminton_ball.csv'
VIDEO_FILE   = ROOT / 'assets' / 'badminton.mp4'
OUT_FILE     = ROOT / 'data' / 'output' / 'badminton_tracked.mp4'

TRAIL_LEN    = 8
BALL_RADIUS  = 8
TRAIL_RADIUS = 5
BALL_COLOR   = (0, 0, 255)
TRAIL_COLOR  = (0, 255, 255)
# ─────────────────────────────────────────────────────────────────────────────


def main():
    df = pd.read_csv(CSV_FILE)

    cap = cv2.VideoCapture(VIDEO_FILE)
    if not cap.isOpened():
        raise FileNotFoundError(f'Cannot open video: {VIDEO_FILE}')

    fps   = cap.get(cv2.CAP_PROP_FPS)
    w     = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    out = cv2.VideoWriter(OUT_FILE, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    if not out.isOpened():
        raise RuntimeError(f'Cannot open VideoWriter for: {OUT_FILE}')

    traj      = []  # rolling buffer of (x, y) positions
    frame_idx = 0

    print(f'Processing {total} frames...')
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        row = df[df['Frame'] == frame_idx]
        if not row.empty and row.iloc[0]['Visibility'] == 1:
            x = int(row.iloc[0]['X'])
            y = int(row.iloc[0]['Y'])
            traj.append((x, y))
            if len(traj) > TRAIL_LEN:
                traj.pop(0)

        # Draw trail dots
        for tx, ty in traj:
            cv2.circle(frame, (tx, ty), TRAIL_RADIUS, TRAIL_COLOR, -1)

        # Draw current ball position on top
        if traj:
            cv2.circle(frame, traj[-1], BALL_RADIUS, BALL_COLOR, -1)

        out.write(frame)
        frame_idx += 1

        if frame_idx % 100 == 0:
            print(f'  {frame_idx}/{total} frames done')

    cap.release()
    out.release()
    print(f'\n✅ Done! Output saved to: {OUT_FILE}')
    print(f'   Total frames written: {frame_idx}')


if __name__ == '__main__':
    main()