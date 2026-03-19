"""
plot_trajectory.py
------------------
Plots the full shuttlecock path as a 2D image.
Color goes from purple (early frames) to yellow (late frames).

Usage:
    python3 plot_trajectory.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
CSV_FILE = 'TrackNetV3/output/badminton_ball.csv'
OUT_FILE = 'TrackNetV3/output/trajectory.png'
DPI      = 150
# ─────────────────────────────────────────────────────────────────────────────

def main():
    df = pd.read_csv(CSV_FILE)

    total_frames  = len(df)
    visible       = df[df['Visibility'] == 1]
    invisible     = df[df['Visibility'] == 0]
    visibility_pct = 100 * len(visible) / total_frames

    print(f'Total frames  : {total_frames}')
    print(f'Ball visible  : {len(visible)} ({visibility_pct:.1f}%)')
    print(f'Ball invisible: {len(invisible)} ({100 - visibility_pct:.1f}%)')

    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot trajectory colored by frame number
    sc = ax.scatter(
        visible['X'], visible['Y'],
        c=visible['Frame'], cmap='plasma',
        s=4, zorder=2, label='Ball detected'
    )

    # Connect consecutive visible points with a faint line
    ax.plot(visible['X'], visible['Y'],
            color='gray', linewidth=0.4, alpha=0.4, zorder=1)

    plt.colorbar(sc, ax=ax, label='Frame number')

    ax.invert_yaxis()
    ax.set_title('Shuttlecock trajectory', fontsize=14)
    ax.set_xlabel('X position (pixels)')
    ax.set_ylabel('Y position (pixels)')

    # Stats annotation
    stats_text = (
        f'Frames: {total_frames}\n'
        f'Visible: {visibility_pct:.1f}%\n'
        f'X range: {int(visible["X"].min())}–{int(visible["X"].max())}\n'
        f'Y range: {int(visible["Y"].min())}–{int(visible["Y"].max())}'
    )
    ax.text(0.02, 0.98, stats_text,
            transform=ax.transAxes,
            verticalalignment='top',
            fontsize=9,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    plt.tight_layout()
    plt.savefig(OUT_FILE, dpi=DPI, bbox_inches='tight')
    print(f'\nSaved to: {OUT_FILE}')


if __name__ == '__main__':
    main()
