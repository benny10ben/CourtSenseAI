import pandas as pd
import os

# ── Config ────────────────────────────────────────────────────────────────────
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[2]
BALL_CSV   = ROOT / 'TrackNetV3' / 'output' / 'badminton_ball.csv'
PLAYER_CSV = ROOT / 'data' / 'output' / 'players_pose_clean.csv'
MASTER_CSV = ROOT / 'data' / 'output' / 'rally_master.csv'
# ─────────────────────────────────────────────────────────────────────────────


def main():
    print("Loading data streams...")

    if not BALL_CSV.exists():
        print(f"❌ Could not find: {BALL_CSV}")
        return
    if not PLAYER_CSV.exists():
        print(f"❌ Could not find: {PLAYER_CSV}")
        return

    # 1. Ball data
    ball_df = pd.read_csv(BALL_CSV)
    ball_df = ball_df.rename(columns={
        'X'         : 'Ball_X',
        'Y'         : 'Ball_Y',
        'Visibility': 'Ball_Vis'
    })
    ball_df = ball_df[['Frame', 'Ball_Vis', 'Ball_X', 'Ball_Y']]

    # 2. Player data — split P1 and P2 into their own columns
    player_df = pd.read_csv(PLAYER_CSV)

    p1_df = player_df[player_df['Player_ID'] == 1].copy()
    p1_df = p1_df.add_prefix('P1_')
    p1_df = p1_df.rename(columns={'P1_Frame': 'Frame'}).drop(columns=['P1_Player_ID'])

    p2_df = player_df[player_df['Player_ID'] == 2].copy()
    p2_df = p2_df.add_prefix('P2_')
    p2_df = p2_df.rename(columns={'P2_Frame': 'Frame'}).drop(columns=['P2_Player_ID'])

    # 3. Merge on Frame — outer join keeps all frames even if one source missed
    print("Fusing data streams...")
    master_df = pd.merge(ball_df, p1_df, on='Frame', how='outer')
    master_df = pd.merge(master_df, p2_df, on='Frame', how='outer')
    master_df = master_df.sort_values(by='Frame').reset_index(drop=True)

    # 4. Fill missing values and enforce integer types
    master_df = master_df.fillna(0)
    for col in master_df.columns:
        master_df[col] = pd.to_numeric(master_df[col], errors='coerce').fillna(0).astype(int)

    # Force Frame to int — outer merge can silently promote to float
    master_df['Frame'] = master_df['Frame'].astype(int)

    master_df.to_csv(MASTER_CSV, index=False)

    print("=" * 50)
    print("✅ FUSION COMPLETE")
    print(f"   Total Frames : {len(master_df)}")
    print(f"   Data Columns : {len(master_df.columns)}")
    print(f"   Saved to     : {MASTER_CSV}")
    print("=" * 50)


if __name__ == '__main__':
    main()