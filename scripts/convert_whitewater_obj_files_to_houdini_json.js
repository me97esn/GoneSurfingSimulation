const fs = require("fs");
const path = require("path");
// const dir = 'D:\\gone_surfing_exports\\medium_wave_left\\white_water'
const dir = "/hdd/gone_surfing_exports/medium_wave_left/white_water";

const fps = 0.041667;
let num_samples = 0;
let num_frames = 0;
let max_num_points = 0;
const frames = [];
const startFrame = 752;
const files = fs
  .readdirSync(dir)
  .sort((a, b) =>
    fs.statSync(path.join(dir, a)).ctime > fs.statSync(path.join(dir, b)).ctime
      ? 1
      : -1
  );

const [, , resultFileURI, startWriteParticlePercent, endWriteParticlePercent] =
  process.argv;

// A pseudo random number generator
//https://svijaykoushik.github.io/blog/2019/10/04/three-awesome-ways-to-generate-random-number-in-javascript/
// r = randomGenerator()
// const randomValue = r.next().value
function* randomGenerator() {
  const seed = 44; // TODO: use an input from the prompt here instead
  let X = seed;
  const a = 1664525;
  const c = 1013904223;
  const m = Math.pow(2, 32);
  function linearCongruentialGenerator() {
    X = (a * X + c) % m;
    return X;
  }
  while (true) {
    yield linearCongruentialGenerator() / m;
  }
}
const random = randomGenerator();

for (const fileName of files) {
  if (fileName.match(/.*obj/)) {
    let num_points_this_frame = 0;
    const frame_data = [];
    console.group(fileName);
    const [timeStr] = fileName.match(/(\d+)\./g);
    // console.log(timeStr)
    const time = (parseFloat(timeStr) - startFrame) * fps;
    // console.log(time)

    const content = fs.readFileSync(path.join(dir, fileName), {
      encoding: "utf8",
      flag: "r",
    });
    const data = content.split("\n");
    for (line of data) {
      const randomValue = random.next().value;
      if (
        line.match(/v .*/) &&
        startWriteParticlePercent <= randomValue &&
        randomValue <= endWriteParticlePercent
      ) {
        num_samples++;
        num_points_this_frame++;
        const [, x, y, z] = line.split(" ");
        const particleId = num_samples;
        const life = 1.01;
        frame_data.push(
          [particleId, life, x, y, z].map((numStr) => Number.parseFloat(numStr))
        );
      }
    }
    frames.push({
      number: num_frames + 1,
      time,
      num_points: num_points_this_frame,
      frame_data,
    });
    max_num_points =
      max_num_points >= num_points_this_frame
        ? max_num_points
        : num_points_this_frame;
    num_frames++;
    console.groupEnd();
  }
}
const attrib_name = ["id", "life", "P"];
const result = {
  header: {
    version: "1.0",
    num_samples,
    num_frames,
    num_points: num_samples,
    num_attrib: attrib_name.length,
    attrib_name,
    attrib_size: [1, 1, 3],
    attrib_data_type: ["l", "f", "f", "f", "f"],
    data_type: "linear",
  },
  cache_data: {
    frames,
  },
};
console.log("Writing the file...", resultFileURI);
// fs.unlinkSync(resultFileURI);
fs.writeFileSync(resultFileURI, JSON.stringify(result));
console.log("Done.");
