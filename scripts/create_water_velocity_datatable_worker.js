const fs = require("fs");
const path = require("path");

const flip_fluid_cache_folder = "/ssd3/flip_fluid_cache/";
const source_folder_name = "flip_fluid_cache_5";

const { workerData, parentPort } = require("worker_threads");
const { fileName } = workerData;

// TODO: use param instead
const minVectorLength = Math.pow(0.075, 2);
const source_folder = path.join(flip_fluid_cache_folder, source_folder_name);
const bakefiles_folder = path.join(source_folder, "bakefiles");

const match = fileName.match(/^(\d+).bobj/);
const [, timeStr] = match;
const time = parseFloat(timeStr);

const result = { coordinates: [], x_values: [], y_values: [], z_values: [] };
const file = fs.readFileSync(path.join(bakefiles_folder, fileName), null);
const blurFile = fs.readFileSync(
  path.join(bakefiles_folder, `blur${fileName}`),
  null
);
const numberOfVertices = file.readUInt32LE();
const bytesPerNumber = 4;
let offset = 0;

for (let i = 0; i < numberOfVertices; i++) {
  //if (i === 20) {
  //  break;
  //}

  /***************
   * x values
   *
   */

  offset += bytesPerNumber;
  const x = file.readFloatLE(offset);
  const blur_x = blurFile.readFloatLE(offset);
  const ue4Y = x;
  const ue4BlurY = blur_x;

  /***************
   * y values
   *
   */

  offset += bytesPerNumber;
  const y = file.readFloatLE(offset);
  const blur_y = blurFile.readFloatLE(offset);
  const ue4Z = y;
  const ue4BlurZ = blur_y;

  /***************
   * z values
   *
   */

  offset += bytesPerNumber;
  const z = file.readFloatLE(offset);
  const blur_z = blurFile.readFloatLE(offset);
  const ue4X = z;
  const ue4BlurX = blur_z;

  /***************
   * Create the data
   *
   */
  // const key = `F${parseFloat(timeStr)}Y${floorY.toFixed(0)}Z${floorZ.toFixed(0)}`
  result.coordinates.push([ue4Y, ue4Z]);
  result.x_values.push(ue4X);
  result.y_values.push(ue4Y);
  result.z_values.push(ue4Z);
}
console.log("done with ", fileName);
parentPort.postMessage({ result });
