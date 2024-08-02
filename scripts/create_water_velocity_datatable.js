const { Worker } = require("worker_threads");
const fs = require("fs");
const path = require("path");

const flip_fluid_cache_folder = "/ssd3/flip_fluid_cache/";
const source_folder_name = "flip_fluid_cache_5";

function runService({ fileName }) {
  return new Promise((resolve, reject) => {
    const worker = new Worker("./create_water_velocity_datatable_worker.js", {
      workerData: { fileName },
    });
    worker.on("message", resolve);
    worker.on("error", reject);
    worker.on("exit", (code) => {
      if (code !== 0) reject(new Error(`stopped with  ${code} exit code`));
    });
  });
}

const [, , resultFolder = "/tmp/water_velocity.json", startFrame, endFrame] =
  process.argv;

async function run() {
  fs.mkdirSync(resultFolder, { recursive: true });

  const source_folder = path.join(flip_fluid_cache_folder, source_folder_name);
  const bakefiles_folder = path.join(source_folder, "bakefiles");
  const workers = {};
  const files = fs.readdirSync(bakefiles_folder);
  for (const fileName of files) {
    const match = fileName.match(/^(\d+).bobj/);
    if (match) {
      const [, timeStr] = match;
      const time = parseFloat(timeStr);
      if (time < startFrame || time > endFrame) {
        continue;
      }
      workers[time] = runService({ fileName });
      console.log("running file ", fileName);
    }
  }
  await Promise.all(Object.values(workers));
  const result = {};
  for (const time in workers) {
    const worker = await workers[time];
    result[time] = worker.result;
  }
  for (const time in result) {
    const resultFileUri = path.join(resultFolder, `${time}.json`);
    console.log(`Writing file ${resultFileUri}`);
    fs.writeFileSync(resultFileUri, JSON.stringify(result[time]));
  }
}

run();
