import pandas as pd
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[2]
INPUT_CSV  = ROOT / 'data' / 'output' / 'players_pose_full.csv'
OUTPUT_CSV = ROOT / 'data' / 'output' / 'players_pose_clean.csv'
# ─────────────────────────────────────────────────────────────────────────────


def main():
    df = pd.read_csv(INPUT_CSV)

    top_ids = df['Player_ID'].value_counts().nlargest(2).index.tolist()
    print(f"Found IDs: {top_ids}. Smoothing trajectories...")

    avg_y        = {pid: df[df['Player_ID'] == pid]['KP16_Y'].mean() for pid in top_ids}
    sorted_by_y  = sorted(avg_y.items(), key=lambda x: x[1])

    top_player_id    = sorted_by_y[0][0]
    bottom_player_id = sorted_by_y[-1][0]

    def remap_id(row):
        # Handle occlusion (0) to prevent misassignment
        if row['KP16_Y'] == 0:
            return 0

        dist_to_top    = abs(row['KP16_Y'] - avg_y[top_player_id])
        dist_to_bottom = abs(row['KP16_Y'] - avg_y[bottom_player_id])
        return 1 if dist_to_top < dist_to_bottom else 2

    df['Clean_ID'] = df.apply(remap_id, axis=1)
    df = df.drop(columns=['Player_ID']).rename(columns={'Clean_ID': 'Player_ID'})

    all_frames = range(df['Frame'].min(), df['Frame'].max() + 1)
    new_rows   = []

    for target_id in [1, 2]:
        player_df = df[df['Player_ID'] == target_id].copy()
        player_df = player_df.drop_duplicates(subset=['Frame'])
        player_df = player_df.set_index('Frame').reindex(all_frames)

        player_df = player_df.interpolate(method='linear', limit_direction='both')
        player_df['Player_ID'] = target_id
        new_rows.append(player_df.reset_index())

    clean_df   = pd.concat(new_rows).sort_values(by=['Frame', 'Player_ID'])
    coord_cols = [c for c in clean_df.columns if '_X' in c or '_Y' in c or 'Box' in c]
    clean_df[coord_cols] = clean_df[coord_cols].fillna(0).astype(int)

    clean_df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ IDs smoothed & missing frames interpolated!")
    print(f"   Clean data saved to: {OUTPUT_CSV}")


if __name__ == '__main__':
    main()