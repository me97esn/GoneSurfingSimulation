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

fig = plt.figure(figsize=(16, 10))

# 3D surface - angled view matching Blender perspective
ax1 = fig.add_subplot(211, projection='3d')
ax1.plot_surface(X, Y, h, cmap='ocean', edgecolor='none', alpha=0.8)
ax1.set_xlabel('X')
ax1.set_ylabel('Y')
ax1.set_zlabel('Height')
ax1.set_title(f'Frame {frame_data["frame"]} - 3D Surface')
# Set Z limits to exaggerate height for visibility
ax1.set_zlim(0, h.max() * 1.2)
# Viewing angle: elevated, looking along Y axis (similar to Blender screenshot)
ax1.view_init(elev=30, azim=-60)

# 2D heatmap - landscape orientation (Y on horizontal axis, X on vertical)
ax2 = fig.add_subplot(212)
im = ax2.pcolormesh(Y, X, h, cmap='ocean', shading='auto')
ax2.set_xlabel('Y')
ax2.set_ylabel('X')
ax2.set_title(f'Frame {frame_data["frame"]} - Height Map (top-down view)')
plt.colorbar(im, ax=ax2, label='Height')

plt.tight_layout()
plt.show()
