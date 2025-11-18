const fs = require("fs");
const path = require("path");

// Configuration
const flip_fluid_cache_folder = "/hdd/flip_fluid_cache/";
const source_folder_name = "flip_fluid_cache_7";
const output_directory = "/hdd/gone_surfing_exports/medium_wave_left";

// Sampling configuration
const position_tolerance = 0.5; // Tolerance for matching position (±0.5 units) - FR-5

// Frame range
const start_frame = 452;
const end_frame = 600;

const source_folder = path.join(flip_fluid_cache_folder, source_folder_name);
const bakefiles_folder = path.join(source_folder, "bakefiles");

console.log(`Starting velocity export with auto-detection of highest velocity vertex`);
console.log(`Processing frames ${start_frame} to ${end_frame}`);

// FR-3: Find vertex with highest velocity magnitude in start frame
console.log(`\n${"=".repeat(60)}`);
console.log(`STEP 1: Finding vertex with highest velocity in frame ${start_frame}`);
console.log("=".repeat(60));

const startFrameFile = `${start_frame.toString().padStart(6, '0')}.bobj`;
console.log(`Looking for file: ${startFrameFile}`);
const bobjPath = path.join(bakefiles_folder, startFrameFile);
const blurBobjPath = path.join(bakefiles_folder, `blur${startFrameFile}`);

if (!fs.existsSync(bobjPath) || !fs.existsSync(blurBobjPath)) {
  console.error(`Error: Start frame files not found:`);
  console.error(`  ${bobjPath}`);
  console.error(`  ${blurBobjPath}`);
  process.exit(1);
}

const file = fs.readFileSync(bobjPath);
const blurFile = fs.readFileSync(blurBobjPath);

const numberOfVertices = file.readUInt32LE(0);
const bytesPerNumber = 4;
let offset = 0;

let maxVelocityMagnitude = 0;
let maxVelocityVertex = null;
let nonZeroCount = 0;

console.log(`Scanning ${numberOfVertices} vertices...`);

for (let i = 0; i < numberOfVertices; i++) {
  offset += bytesPerNumber;
  const x = file.readFloatLE(offset);
  const blur_x = blurFile.readFloatLE(offset);

  offset += bytesPerNumber;
  const y = file.readFloatLE(offset);
  const blur_y = blurFile.readFloatLE(offset);

  offset += bytesPerNumber;
  const z = file.readFloatLE(offset);
  const blur_z = blurFile.readFloatLE(offset);

  // Track non-zero velocities for debugging
  if (blur_x !== 0 || blur_y !== 0 || blur_z !== 0) {
    nonZeroCount++;
    if (nonZeroCount <= 5) {
      console.log(`  Non-zero velocity #${nonZeroCount}: blur=(${blur_x.toFixed(4)}, ${blur_y.toFixed(4)}, ${blur_z.toFixed(4)}) at pos=(${x.toFixed(2)}, ${y.toFixed(2)}, ${z.toFixed(2)})`);
    }
  }

  // FR-3: Calculate sum of blur components: blur.x + blur.y + blur.z
  const velocitySum = blur_x + blur_y + blur_z;

  if (velocitySum > maxVelocityMagnitude) {
    maxVelocityMagnitude = velocitySum;
    maxVelocityVertex = { x, y, z, blur_x, blur_y, blur_z };
  }
}

console.log(`\nFound ${nonZeroCount} vertices with non-zero velocity out of ${numberOfVertices} total`);

if (maxVelocityVertex === null || maxVelocityMagnitude === 0) {
  console.error(`\nError: No vertices with velocity found! All blur values are zero.`);
  console.error(`This might indicate:`);
  console.error(`  1. Motion blur data was not generated in the simulation`);
  console.error(`  2. The blur*.bobj files are empty or corrupted`);
  console.error(`  3. The frame selected has no motion`);
  process.exit(1);
}

console.log(`\nFound vertex with highest velocity sum (blur.x + blur.y + blur.z): ${maxVelocityMagnitude.toFixed(4)}`);
console.log(`Position: x=${maxVelocityVertex.x.toFixed(2)}, y=${maxVelocityVertex.y.toFixed(2)}, z=${maxVelocityVertex.z.toFixed(2)}`);
console.log(`Blur data (velocities):`);
console.log(`  blur.x = ${maxVelocityVertex.blur_x.toFixed(4)}`);
console.log(`  blur.y = ${maxVelocityVertex.blur_y.toFixed(4)}`);
console.log(`  blur.z = ${maxVelocityVertex.blur_z.toFixed(4)}`);
console.log(`  sum    = ${maxVelocityMagnitude.toFixed(4)}`);

// FR-4: Create three output files, one for each axis
console.log(`\n${"=".repeat(60)}`);
console.log(`STEP 2: Sampling along three axes`);
console.log("=".repeat(60));

const axes = [
  { name: 'x', fixedCoord: maxVelocityVertex.x, axis1: 'y', axis2: 'z', outputFile: 'wave-velocity-line-x.json' },
  { name: 'y', fixedCoord: maxVelocityVertex.y, axis1: 'x', axis2: 'z', outputFile: 'wave-velocity-line-y.json' },
  { name: 'z', fixedCoord: maxVelocityVertex.z, axis1: 'x', axis2: 'y', outputFile: 'wave-velocity-line-z.json' }
];

// Get list of all bobj files
const files = fs.readdirSync(bakefiles_folder);
const fileList = [];

for (const fileName of files) {
  const match = fileName.match(/^(\d+)\.bobj$/);
  if (match) {
    const [, frameStr] = match;
    const frameNumber = parseInt(frameStr);
    if (frameNumber >= start_frame && frameNumber <= end_frame) {
      fileList.push({ frameNumber, fileName });
    }
  }
}

fileList.sort((a, b) => a.frameNumber - b.frameNumber);
console.log(`Found ${fileList.length} files to process`);

// Process each axis
for (const axisConfig of axes) {
  console.log(`\n${"-".repeat(60)}`);
  console.log(`Processing ${axisConfig.name.toUpperCase()}-axis: sampling along ${axisConfig.axis1} and ${axisConfig.axis2} at ${axisConfig.name}=${axisConfig.fixedCoord.toFixed(2)}`);
  console.log("-".repeat(60));

  const frames_data = [];

  for (const { frameNumber, fileName } of fileList) {
    const frame_data = {
      Name: `Frame_${frameNumber}`,
      Positions: [],
      Velocities: []
    };

    const bobjPath = path.join(bakefiles_folder, fileName);
    const blurBobjPath = path.join(bakefiles_folder, `blur${fileName}`);

    if (!fs.existsSync(bobjPath) || !fs.existsSync(blurBobjPath)) {
      console.log(`  Skipping frame ${frameNumber}: files not found`);
      continue;
    }

    const file = fs.readFileSync(bobjPath);
    const blurFile = fs.readFileSync(blurBobjPath);

    const numberOfVertices = file.readUInt32LE(0);
    let offset = 0;
    let samplesCount = 0;

    for (let i = 0; i < numberOfVertices; i++) {
      offset += bytesPerNumber;
      const x = file.readFloatLE(offset);
      const blur_x = blurFile.readFloatLE(offset);

      offset += bytesPerNumber;
      const y = file.readFloatLE(offset);
      const blur_y = blurFile.readFloatLE(offset);

      offset += bytesPerNumber;
      const z = file.readFloatLE(offset);
      const blur_z = blurFile.readFloatLE(offset);

      // Check if vertex is on the line for this axis
      let isOnLine = false;
      if (axisConfig.name === 'x') {
        isOnLine = Math.abs(x - axisConfig.fixedCoord) <= position_tolerance;
      } else if (axisConfig.name === 'y') {
        isOnLine = Math.abs(y - axisConfig.fixedCoord) <= position_tolerance;
      } else if (axisConfig.name === 'z') {
        isOnLine = Math.abs(z - axisConfig.fixedCoord) <= position_tolerance;
      }

      if (isOnLine) {
        frame_data.Positions.push({ X: x, Y: y, Z: z });
        frame_data.Velocities.push({ X: blur_x, Y: blur_y, Z: blur_z });
        samplesCount++;
      }
    }

    if (frameNumber === start_frame || frameNumber % 20 === 0) {
      console.log(`  Frame ${frameNumber}: ${samplesCount} samples`);
    }

    frames_data.push(frame_data);
  }

  // Write output file for this axis
  fs.mkdirSync(output_directory, { recursive: true });
  const output_filepath = path.join(output_directory, axisConfig.outputFile);
  fs.writeFileSync(output_filepath, JSON.stringify(frames_data, null, 2));

  const totalSamples = frames_data.reduce((sum, frame) => sum + frame.Positions.length, 0);
  const avgSamples = (totalSamples / frames_data.length).toFixed(1);

  console.log(`\n  ✓ Output written: ${axisConfig.outputFile}`);
  console.log(`    Total frames: ${frames_data.length}`);
  console.log(`    Total samples: ${totalSamples}`);
  console.log(`    Average samples per frame: ${avgSamples}`);
}

console.log(`\n${"=".repeat(60)}`);
console.log("EXPORT COMPLETED!");
console.log("=".repeat(60));
console.log(`Output directory: ${output_directory}`);
console.log(`Files created:`);
for (const axisConfig of axes) {
  console.log(`  - ${axisConfig.outputFile}`);
}
console.log("=".repeat(60));
