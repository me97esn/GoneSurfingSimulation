"""
Plot height samples from a unified wave data frame file as a 3D surface.

Usage:
    python plot_unified_wave_data.py <frame_json_file>

Example:
    python plot_unified_wave_data.py /hdd/gone_surfing_exports/medium_wave_left/unified/wave_data_frame_886.json
"""
import json
import sys
import numpy as np
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    print("Usage: python plot_unified_wave_data.py <frame_json_file>")
    sys.exit(1)

filepath = sys.argv[1]

with open(filepath) as f:
    frame_data = json.load(f)

grid = frame_data['grid']
width = grid['width']
height = grid['height']
step = grid['step']
start_x = grid['start_x']
start_y = grid['start_y']

h = np.array(frame_data['data']['h']).reshape(height, width)

x = np.array([start_x + step * i for i in range(width)])
y = np.array([start_y + step * j for j in range(height)])
X, Y = np.meshgrid(x, y)

# Count zero vs nonzero
total = width * height
nonzero = np.count_nonzero(h)
print(f"Frame: {frame_data['frame']}")
print(f"Grid: {width} x {height} = {total} samples, step={step}")
print(f"Grid start: ({start_x}, {start_y})")
print(f"Height range: [{h.min():.3f}, {h.max():.3f}]")
print(f"Non-zero samples: {nonzero}/{total} ({100*nonzero/total:.1f}%)")

fig = plt.figure(figsize=(14, 6))

# 3D surface
ax1 = fig.add_subplot(121, projection='3d')
ax1.plot_surface(X, Y, h, cmap='ocean', edgecolor='none', alpha=0.8)
ax1.set_xlabel('X')
ax1.set_ylabel('Y')
ax1.set_zlabel('Height')
ax1.set_title(f'Frame {frame_data["frame"]} - 3D Surface')

# 2D heatmap
ax2 = fig.add_subplot(122)
im = ax2.pcolormesh(X, Y, h, cmap='ocean', shading='auto')
ax2.set_xlabel('X')
ax2.set_ylabel('Y')
ax2.set_title(f'Frame {frame_data["frame"]} - Height Map')
ax2.set_aspect('equal')
plt.colorbar(im, ax=ax2, label='Height')

plt.tight_layout()
plt.show()
