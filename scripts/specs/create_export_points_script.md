# Spec: create-script-for-exporting-ocean-surface-samples

## Overview

This exports the samples of the ocean surface in a format that can be imported into Unreal.

## Objective

This should create a script that can be run in blender, that exports all of the samples.

## Requirements

### Functional Requirements

1. **FR-1**: The implementation shall create a script in the same folder as export_fluid_surface_to_3d_samples.py
2. **FR-2**: The created script should be similar to export_fluid_surface_to_3d_samples.py, but write the data in another format to another file.
3. **FR-3**: The created script should write json to a file with the format as in the WavePointsData_Example.json file.
4. **FR-4**: The keys for each row should be in the format "Frame_752" where the number is the frame number.
5. **FR-5**: The result json file should be named ocean-points-data.json
6. **FR-6**: The script file should be a python file
7. **FR-7**: Make sure that the python file is correctly indented and compiles
8. **FR-8**: The script should add another array of floats, for scale. The scale should be calculated using the direction of the normal for this sample.
9. **FR-9**: If the height difference between this raycast and the previous raycast in the X Axis is above a configurable value, this raycast should be skipped. Neither its position, normal nor scale should be stored. Same thing if the height difference compared to the next raycast in the same axis, the results of this raycast should be skipped.
10. **FR-10**: At the end of the script: print how many samples have been written in total, and how many per resolution was written.
11. **FR-11**: I have added a mesh named 'High_resolution_boundary' to the blender file. Only samples within the boundaries of this mesh should be handled in the **FR-9** requirement.
12. **FR-12**: The samples identified in **FR-9** and **FR-11** should no longer be skipped. Quite the opposite: these samples should be run with half the step size as the other samples, resulting in more samples with shorter distance between.
13. **FR-13**: Since I now use varying step size for the sampling, this has to be stored in the result as well. Write this into the frame_date["Scales"], with value for each sample being size of this step divided by the original size of the step. Example: step=5, currentStep=5, scale=1
14. **FR-14**: The scale calculated in **FR-13** should also be multiplied with 1/cos of the normal. Steeper samples should have higher scale. This should be included both for the high resolution and low resolution samples.
15. **FR-15**: The high resolution grid and the low resolution grid should align
16. **FR-16**: The highest 1% of the samples should also use high resolution.
17. **FR-17**: The scale of any of the samples should never exceed 3.0
18. **FR-18**: The samples with steepest normals should be handled differently. They should be ignored from the original sampling, and instead use a separate ray_cast. This separate ray_cast should be sideways or front-to-back instead of straight down. I don't know at the time of wrighting which of the directions should be used, it should be Configurable. This separate ray_cast should be done over the entire model, since the vertical sampling might miss some steep areas.
19. **FR-19**: The steep normal samples should also have their scale calculated the same way as the other samples.
20. **FR-20**: The steep normal samples should also be limited to a maximum scale of 3.0
21. **FR-21**: Introduce an even lower resolution sampling for the areas outside the high resolution boundary. This low resolution sampling should have double the step size of the original low resolution sampling.
22. **FR-22**: The samples from the even lower resolution sampling should also have their scale calculated the same way as the other samples.
23. **FR-23**: The samples from the steep waves should also use high resolution sampling.
24. **FR-24**: The scales of the lower sample blocks should be adjusted just as the high resolution samle blocks are.
25. **FR-25**: No blocks with normal steeper then the steep_normal_threshold should have lower resolution then high. Any blocks steeper then this threshold and found with the low or lower resolution ray tracing should be skipped.
26. **FR-26**: The steeper sampling should be configurable to perform tracing from 4 directions: -x, x, -y, y.
27. **FR-27**: the high resolution grid, low resolution grid and lower resolution grid should all align.
28. **FR-28**: The steeper sampling should only use high resolution sampling, but only include those hits with normal steeper then in **FR-18**.
29. **FR-29**: All sampling (steep and vertical) should NOT use cos between normal and z axis when calculating scale, since this makes the scale way too big for steep samples. Instead, all samples should use cos between the normal and the trace direction when calculating scale. For vertical rays, the trace direction is downward (0, 0, -1). For horizontal rays (steep sampling), the trace direction is the actual ray direction (x, -x, y, or -y).
30. **FR-30**: Samples where the surface normal is too perpendicular to the ray direction should be skipped to avoid excessively large scales. Add a configurable threshold `min_cos_trace` (minimum cosine between normal and trace direction). If `abs(normal.dot(ray_direction)) < min_cos_trace`, the sample should be skipped. This applies to all sampling types (vertical, horizontal steep sampling). A suggested default value is 0.25 (corresponding to ~75 degrees from perpendicular, or ~15 degrees from parallel), which would prevent scales from exceeding 4.0 even before the max_scale clamp is applied.
31. **FR-31**: The script should no longer use difference in height from **FR-9**, since this misses some samples with high volatility. It should instead look at the normal of the current sample only. If the normal of the current sample is steep enough, higher resolution should be used. Close to no slope: low resolution. Moderate slope: medium resolution. Steep slope: high resolution. Note that only the current sample is of interest for this, the next or previous sample can be ignored when deciding resolution. **FR-18**, **FR-16**, **FR-11** should still apply.
32. **FR-32**: The script should split the results into separate files, one for each direction of the ray cast.
33. **FR-33**: The highest 1% of the samples in **FR-16** should use even higher resolution.
34. **FR-34**: There are some gaps when the low resolution meet medium resolution. If this is because of a bug it should be fixed, otherwise an extra row of medium resolution samples can be added in these areas to minimize the risk of gaps.
35. **FR-35**: The **FR-9**, **FR-11**, **FR-12**, **FR-22**,**FR-24**,**FR-31**, **FR-34** no longer apply. Instead: first identify the highest 1% of the samples each frame. The samples for these highest points should be made with the highest resolution. Gradually decrease the resolution with distence to the highest samples, so that at the two y edges it has the lowest resolution. But all along the highest peak, which spans between the x edges, there should be highest resolution. The resolution don't have to be in discreet steps, it can also be gradual.
36. **FR-36**: All of the samples should align, and there should be no gaps between them.
37. **FR-37**: The scaling of the sampling should be as before: adjusted by both normal and step size.
38. **FR-38**: The skipping of too steep samples from the vertical sampling still applies.
39. **FR-39**: The ridge of higher resolution should be around 5 samples wide in the positive y direction, and 10 samples wide in the negative y direction. Then there should be around 5 rows of high samples in the negative y direction, and around two in the positive y direction. Then a few rows of medium resolution in both directions before low resolution is used. The goal of this is to get high resolution at the wave, but with as little data as possible while still keeping a high detail of the wave. The exact number of rows per resolution is not important, prioritise aligning them if another number makes it easier to align the samples without increasing the amount of data too much.

### Non-Functional Requirements

1. **NFR-1**: The implementation shall be simple and readable
2. **NFR-2**: The code shall follow project coding standards

## Acceptance Criteria

## Implementation Details

## Notes for AI Agent

- Implement as a python script

## Status

- [x] Specification written
- [x] Implementation complete
- [x] Tests passing
- [ ] Code reviewed
- [ ] Merged to main

## Implementation Notes

- Created export_ocean_points.py in /home/emil/workspace/GoneSurfingSimulation/scripts/
- Script follows the same structure as export_fluid_surface_to_3d_samples.py
- Outputs JSON in the format matching WavePointsData_Example.json with Frame_XXX keys
- Output file: ocean-points-data.json
- Script successfully compiles with proper indentation
- Added configurable max_height_difference threshold (default: 5.0) for FR-9
- Implemented two-pass approach: first collects all raycasts, then filters based on height differences
- Height difference checking compares each sample with both previous and next samples in X axis
- Added statistics tracking and reporting (FR-10):
  - Total samples written count
  - Samples per resolution: low (2x step), medium (1x step), high (0.5x step)
  - Samples skipped count
  - Percentage of skipped samples
- Scale calculation based on normal direction (FR-8) already implemented
- FR-26 implemented: Steep normal ray casting now supports 4 configurable directions (-x, x, -y, y)
  - Changed `steep_ray_direction` (single value) to `steep_ray_directions` (list)
  - All configured directions are processed in a loop
  - Default configuration includes all 4 directions: ['x', '-x', 'y', '-y']
- FR-27 implemented: All grids properly align
  - High-res grid uses step/2 with quarter_step offsets, centered on low-res grid
  - Low-res grid uses step at original grid positions
  - Lower-res grid uses double step size, sampling every other point (x % 2 == 0 and y % 2 == 0)
  - All three grids are aligned to ensure consistent spacing
- FR-28 implemented: Steep sampling always uses high resolution
  - Removed conditional step sizing for steep samples
  - All steep normal samples now use step/2 (high resolution) regardless of location
  - Step scale is always 0.5 for steep samples
- FR-29 implemented: All scale calculations now use cos between normal and trace direction
  - Steep horizontal sampling: Uses cos between normal and ray_direction_vec (x or y direction)
  - Vertical sampling (high-res): Uses cos between normal and ray_direction (downward)
  - Vertical sampling (low/lower-res): Uses cos between normal and vertical_ray_direction (0, 0, -1)
  - This prevents excessively large scales for steep samples by using the actual trace direction instead of z-axis
- FR-30 implemented: Samples too perpendicular to ray direction are now skipped
  - Added configurable threshold `min_cos_trace` = 0.25 (default)
  - Samples with `abs(normal.dot(ray_direction)) < min_cos_trace` are skipped
  - Applied to all sampling types: steep horizontal rays (x, -x, y, -y) and all vertical rays (high-res, normal, low-res)
  - This prevents samples with excessively large scales caused by near-perpendicular surfaces
  - With min_cos_trace = 0.25, maximum normal_scale is limited to 4.0 before max_scale clamp is applied
- FR-31 implemented: Resolution selection now based on surface normal steepness (replaces height difference checking)
  - Removed height difference checking logic (FR-9, FR-12)
  - Added configurable thresholds: `low_res_threshold` = 0.95, `medium_res_threshold` = 0.7
  - Resolution determined by `abs(normal.z)`: flat surfaces (>0.95) use low resolution (2x step), moderate slopes (0.7-0.95) use medium resolution (1x step), steep slopes (<0.7) use high resolution (0.5x step)
  - FR-11, FR-16, FR-18 still apply: high resolution boundary enforces at least medium resolution, top 1% uses high resolution, steep normals handled by sideways ray casting
  - Each sample's resolution is determined independently based only on its own normal
- FR-32 implemented: Results split into separate files per ray direction
  - Data structure changed to `frame_data_by_direction` with separate tracking for each direction: 'vertical', 'x', '-x', 'y', '-y'
  - Each ray direction writes to its own file: `ocean-points-data-vertical.json`, `ocean-points-data-x.json`, `ocean-points-data--x.json`, `ocean-points-data-y.json`, `ocean-points-data--y.json`
  - Allows independent processing and analysis of samples from different ray directions
  - Vertical rays capture the main surface, horizontal rays capture steep features from multiple angles
- FR-33 implemented: Highest 1% samples use extra-high resolution
  - Top 1% samples now use `extra_high` resolution level instead of just `high`
  - Extra-high resolution uses step/4 spacing (16 samples per grid cell)
  - Step scale is 0.25 for extra-high resolution samples
  - Provides even denser sampling at wave peaks and critical areas
- FR-34 implemented: Boundary samples prevent gaps between resolution levels (superseded by FR-35)
  - Added neighbor checking to detect resolution boundaries
  - When low-resolution cell is adjacent to medium/high/extra-high resolution cell, it upgrades to medium resolution
  - This creates a transition zone that prevents gaps at resolution boundaries
  - Ensures continuous coverage across the entire surface
- FR-35 implemented: Complete redesign with distance-based resolution system
  - Removed normal-steepness-based resolution (FR-9, FR-11, FR-12, FR-22, FR-24, FR-31, FR-34 no longer apply)
  - First pass: coarse sampling at base resolution to identify highest 1% of samples
  - Identifies y-positions of peak samples (highest 1%) which define the "peak line" along x-axis
  - Resolution gradually decreases with distance from peaks: highest at peaks, lowest at y edges
  - Resolution is continuous/gradual rather than discrete steps
  - Uses `calculate_distance_based_step_multiplier()` function to determine step size based on distance from peak
  - Peak region (20% of y_length): interpolates from min_step_multiplier (0.25) to 1.0
  - Outside peak region: interpolates from 1.0 to max_step_multiplier (2.0) based on distance from peak region
  - Along entire x-axis at peak height: maintains highest resolution
- FR-36 implemented: All samples align with no gaps
  - Uses finest resolution (base_step * min_step_multiplier) as base grid
  - Samples only at positions that align with local resolution using alignment check
  - Position must align in both x and y with the local step size
  - Prevents gaps by ensuring consistent grid alignment across variable resolution regions
- FR-37 implemented: Scale adjustment by both normal and step size maintained
  - All samples calculate scale as: step_scale * normal_scale
  - step_scale = step_multiplier (for vertical) or high_res_step/base_step (for horizontal steep)
  - normal_scale = 1 / cos(normal, ray_direction)
  - Combined scale clamped to max_scale (4.0)
- FR-38 implemented: Steep samples skipped from vertical sampling
  - Vertical sampling checks `is_steep_normal()` and skips if true
  - Steep samples only handled by horizontal ray casting (FR-18)
  - This prevents duplicate/conflicting samples from vertical and horizontal directions
- FR-39 implemented: Asymmetric resolution distribution around wave ridge
  - Replaced gradual interpolation with discrete resolution zones
  - **Ridge (0.25x step)**: ~5 samples wide in +y direction, ~10 samples wide in -y direction
  - **High resolution (0.5x step)**: ~2 rows in +y direction, ~5 rows in -y direction
  - **Medium resolution (1.0x step)**: ~3 rows in both directions
  - **Low resolution (2.0x step)**: Beyond medium zone
  - Asymmetric distribution optimizes data size while maintaining wave detail
  - Uses signed distance from peak to determine direction (+y vs -y)
  - Zone extents calculated based on base_step and resolution multipliers
  - Ensures alignment by using consistent step sizes within each zone
