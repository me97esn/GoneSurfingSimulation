const fs = require("fs");
const path = require("path");

// Directory containing white water OBJ files
// const dir = 'D:\\gone_surfing_exports\\medium_wave_left\\white_water'
const dir = "/hdd/gone_surfing_exports/medium_wave_left/white_water";

const startFrame = 752;
const frames = [];

// FR-7: Configurable Z-axis rotation (in degrees, clockwise)
const rotationDegrees = 90; // Default: 90 degrees clockwise
const rotationRadians = (rotationDegrees * Math.PI) / 180;

// Rotation matrix for Z-axis (clockwise rotation)
function rotateAroundZ(x, y, z, angle) {
  // Clockwise rotation: x' = x*cos(θ) + y*sin(θ), y' = -x*sin(θ) + y*cos(θ)
  const cosAngle = Math.cos(angle);
  const sinAngle = Math.sin(angle);
  return {
    x: x * cosAngle + y * sinAngle,
    y: -x * sinAngle + y * cosAngle,
    z: z
  };
}

// Get command line arguments
const [, , resultFileURI] = process.argv;

// Read and sort files by creation time
const files = fs
  .readdirSync(dir)
  .sort((a, b) =>
    fs.statSync(path.join(dir, a)).ctime > fs.statSync(path.join(dir, b)).ctime ? 1 : -1
  );

console.log(`Processing ${files.length} files...`);

// Process each OBJ file
for (const fileName of files) {
  if (fileName.match(/.*obj/)) {
    // Extract frame number from filename
    const [timeStr] = fileName.match(/(\d+)\./g);
    const frameNumber = parseInt(timeStr);

    console.log(`Processing ${fileName} (Frame ${frameNumber})...`);

    // Read OBJ file content
    const content = fs.readFileSync(path.join(dir, fileName), {
      encoding: "utf8",
      flag: "r",
    });

    // Parse vertices from OBJ file
    const positions = [];
    const lines = content.split("\n");

    for (const line of lines) {
      // Check if line contains vertex data (starts with "v ")
      if (line.match(/^v /)) {
        const [, x, y, z] = line.split(" ");
        // FR-7: Apply Z-axis rotation
        const rotated = rotateAroundZ(parseFloat(x), parseFloat(y), parseFloat(z), rotationRadians);
        positions.push({
          X: rotated.x,
          Y: rotated.y,
          Z: rotated.z
        });
      }
    }

    // Create frame data in WavePointsData format
    frames.push({
      Name: `Frame_${frameNumber}`,
      Positions: positions,
      Normals: [], // Empty as per FR-5
      Scales: []   // Empty as per FR-5
    });

    console.log(`  Particles in frame: ${positions.length}`);
  }
}

// Write result to file
const outputPath = resultFileURI || path.join(dir, "white-water-points-data.json");
console.log(`\nWriting output to ${outputPath}...`);
fs.writeFileSync(outputPath, JSON.stringify(frames, null, 2));

const totalParticles = frames.reduce((sum, frame) => sum + frame.Positions.length, 0);
console.log("\nExport completed!");
console.log(`Total frames: ${frames.length}`);
console.log(`Total particles: ${totalParticles}`);
console.log(`Average particles per frame: ${(totalParticles / frames.length).toFixed(2)}`);
