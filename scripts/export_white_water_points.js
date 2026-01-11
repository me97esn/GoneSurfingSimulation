const fs = require("fs");
const path = require("path");

// Directory containing white water OBJ files
// const dir = 'D:\\gone_surfing_exports\\medium_wave_left\\white_water'
const dir = "/hdd/gone_surfing_exports/medium_wave_left/white_water";

// Parse command-line arguments for start and end frame
// Usage: node export_white_water_points.js [start_frame] [end_frame] [frame_step]
const args = process.argv.slice(2);
const startFrame = args[0] ? parseInt(args[0]) : 752;
const endFrame = args[1] ? parseInt(args[1]) : null; // null means process all files
const frameStep = args[2] ? parseInt(args[2]) : 5; // Export every Nth frame (default: 5)

console.log(`Start frame: ${startFrame}`);
if (endFrame) {
  console.log(`End frame: ${endFrame}`);
}
console.log(`Frame step: ${frameStep} (exporting every ${frameStep}${frameStep === 1 ? 'st' : frameStep === 2 ? 'nd' : frameStep === 3 ? 'rd' : 'th'} frame)`);

const rotationDegrees = 90; // 90 degrees rotation for each axis
const rotationRadians = (rotationDegrees * Math.PI) / 180;

// Rotation functions for each axis (90 degrees clockwise when looking down the positive axis)
function rotateAroundX(x, y, z, angle) {
  // X-axis rotation: y' = y*cos(θ) + z*sin(θ), z' = -y*sin(θ) + z*cos(θ), x' = x
  const cosAngle = Math.cos(angle);
  const sinAngle = Math.sin(angle);
  return {
    x: x,
    y: y * cosAngle + z * sinAngle,
    z: -y * sinAngle + z * cosAngle
  };
}

function rotateAroundY(x, y, z, angle) {
  // Y-axis rotation: x' = x*cos(θ) - z*sin(θ), z' = x*sin(θ) + z*cos(θ), y' = y
  const cosAngle = Math.cos(angle);
  const sinAngle = Math.sin(angle);
  return {
    x: x * cosAngle - z * sinAngle,
    y: y,
    z: x * sinAngle + z * cosAngle
  };
}

function rotateAroundZ(x, y, z, angle) {
  // Z-axis rotation: x' = x*cos(θ) + y*sin(θ), y' = -x*sin(θ) + y*cos(θ), z' = z
  const cosAngle = Math.cos(angle);
  const sinAngle = Math.sin(angle);
  return {
    x: x * cosAngle + y * sinAngle,
    y: -x * sinAngle + y * cosAngle,
    z: z
  };
}

// Data structures for each rotation axis
const framesX = [];
const framesY = [];
const framesZ = [];

// Read, filter, and sort files by frame number (not creation time)
const allFiles = fs
  .readdirSync(dir)
  .filter(f => f.match(/.*\.obj$/));

// Filter files by frame range, frame step, and sort by frame number
const files = allFiles
  .map(fileName => {
    const match = fileName.match(/(\d+)\./);
    return match ? { fileName, frameNumber: parseInt(match[1]) } : null;
  })
  .filter(item => {
    if (!item) return false;
    if (item.frameNumber < startFrame) return false;
    if (endFrame && item.frameNumber > endFrame) return false;
    // Only include frames that match the step pattern (e.g., every 5th frame)
    if ((item.frameNumber - startFrame) % frameStep !== 0) return false;
    return true;
  })
  .sort((a, b) => a.frameNumber - b.frameNumber)
  .map(item => item.fileName);

console.log(`Processing ${files.length} files (of ${allFiles.length} total)...`);
console.log(`Creating 3 output files, each rotated ${rotationDegrees}° around a single axis (X, Y, or Z)\n`);

// Process each OBJ file
for (const fileName of files) {
  // Extract frame number from filename
  const [timeStr] = fileName.match(/(\d+)\./g);
  const frameNumber = parseInt(timeStr);

  console.log(`Processing ${fileName} (Frame ${frameNumber})...`);

  // Read OBJ file content
  const content = fs.readFileSync(path.join(dir, fileName), {
    encoding: "utf8",
    flag: "r",
  });

  // Parse vertices from OBJ file - create separate position arrays for each rotation
  const positionsX = [];
  const positionsY = [];
  const positionsZ = [];
  const lines = content.split("\n");

  // Debug: track first vertex for rotation verification
  let firstVertex = null;
  let firstVertexX = null;
  let firstVertexY = null;
  let firstVertexZ = null;

  for (const line of lines) {
    // Check if line contains vertex data (starts with "v ")
    if (line.match(/^v /)) {
      const [, x, y, z] = line.split(" ");
      const xNum = parseFloat(x);
      const yNum = parseFloat(y);
      const zNum = parseFloat(z);

      // Apply rotation around X-axis
      const rotatedX = rotateAroundX(xNum, yNum, zNum, rotationRadians);
      positionsX.push({
        X: rotatedX.x,
        Y: rotatedX.y,
        Z: rotatedX.z
      });

      // Apply rotation around Y-axis
      const rotatedY = rotateAroundY(xNum, yNum, zNum, rotationRadians);
      positionsY.push({
        X: rotatedY.x,
        Y: rotatedY.y,
        Z: rotatedY.z
      });

      // Apply rotation around Z-axis
      const rotatedZ = rotateAroundZ(xNum, yNum, zNum, rotationRadians);
      positionsZ.push({
        X: rotatedZ.x,
        Y: rotatedZ.y,
        Z: rotatedZ.z
      });

      // Debug: capture first vertex for logging
      if (!firstVertex) {
        firstVertex = { x: xNum, y: yNum, z: zNum };
        firstVertexX = rotatedX;
        firstVertexY = rotatedY;
        firstVertexZ = rotatedZ;
      }
    }
  }

  // Debug output for first vertex of first frame
  if (firstVertex && frameNumber === startFrame) {
    console.log(`  First vertex ORIGINAL: (${firstVertex.x.toFixed(3)}, ${firstVertex.y.toFixed(3)}, ${firstVertex.z.toFixed(3)})`);
    console.log(`  After X-axis rotation:  (${firstVertexX.x.toFixed(3)}, ${firstVertexX.y.toFixed(3)}, ${firstVertexX.z.toFixed(3)})`);
    console.log(`  After Y-axis rotation:  (${firstVertexY.x.toFixed(3)}, ${firstVertexY.y.toFixed(3)}, ${firstVertexY.z.toFixed(3)})`);
    console.log(`  After Z-axis rotation:  (${firstVertexZ.x.toFixed(3)}, ${firstVertexZ.y.toFixed(3)}, ${firstVertexZ.z.toFixed(3)})`);
  }

  // Create frame data in WavePointsData format for each rotation
  framesX.push({
    Name: `Frame_${frameNumber}`,
    Positions: positionsX
  });

  framesY.push({
    Name: `Frame_${frameNumber}`,
    Positions: positionsY
  });

  framesZ.push({
    Name: `Frame_${frameNumber}`,
    Positions: positionsZ
  });

  console.log(`  Particles in frame: ${positionsX.length}`);
}

// Write three separate output files
const baseOutputPath = path.join(dir, "white-water-points-data");

const outputPathX = `${baseOutputPath}-rotX.json`;
const outputPathY = `${baseOutputPath}-rotY.json`;
const outputPathZ = `${baseOutputPath}-rotZ.json`;

console.log(`\nWriting output files...`);
fs.writeFileSync(outputPathX, JSON.stringify(framesX, null, 2));
console.log(`  X-axis rotation: ${outputPathX}`);

fs.writeFileSync(outputPathY, JSON.stringify(framesY, null, 2));
console.log(`  Y-axis rotation: ${outputPathY}`);

fs.writeFileSync(outputPathZ, JSON.stringify(framesZ, null, 2));
console.log(`  Z-axis rotation: ${outputPathZ}`);

const totalParticles = framesX.reduce((sum, frame) => sum + frame.Positions.length, 0);
console.log("\n" + "=".repeat(60));
console.log("EXPORT COMPLETED!");
console.log("=".repeat(60));
console.log(`Total frames per file: ${framesX.length}`);
console.log(`Total particles per file: ${totalParticles}`);
console.log(`Average particles per frame: ${(totalParticles / framesX.length).toFixed(2)}`);
console.log("\nThree files created:");
console.log(`  1. ${path.basename(outputPathX)} - Rotated 90° around X-axis`);
console.log(`  2. ${path.basename(outputPathY)} - Rotated 90° around Y-axis`);
console.log(`  3. ${path.basename(outputPathZ)} - Rotated 90° around Z-axis`);
console.log("\nCompare these files in Unreal Engine to determine the correct rotation axis.");
console.log("=".repeat(60));
