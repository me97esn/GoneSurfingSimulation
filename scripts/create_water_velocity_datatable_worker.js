const fs = require("fs");
const path = require("path");

const flip_fluid_cache_folder = "/ssd3/flip_fluid_cache/";
const source_folder_name = "flip_fluid_cache_6";

const { workerData, parentPort } = require("worker_threads");
const { fileName } = workerData;

const source_folder = path.join(flip_fluid_cache_folder, source_folder_name);
const bakefiles_folder = path.join(source_folder, "bakefiles");

const result = {
  coordinates: [],
  x_coordinates: [],
  y_coordinates: [],
  z_coordinates: [],
  dx: [],
  dy: [],
  dz: [],
  height: [],
};
const file = fs.readFileSync(path.join(bakefiles_folder, fileName), null);
const blurFile = fs.readFileSync(
  path.join(bakefiles_folder, `blur${fileName}`),
  null
);
const numberOfVertices = file.readUInt32LE();
const bytesPerNumber = 4;
let offset = 0;
//const key = F${parseFloat(timeStr)}Y${floorY.toFixed(0)}Z${floorZ.toFixed(0)}
const vertices = [];
for (let i = 0; i < numberOfVertices; i++) {
  //if (i === 4000) {
  //  break;
  //}

  /***************
   * x values
   *
   */

  offset += bytesPerNumber;
  const x = file.readFloatLE(offset);
  const blur_x = blurFile.readFloatLE(offset);

  /***************
   * y values
   *
   */

  offset += bytesPerNumber;
  const y = file.readFloatLE(offset);
  const blur_y = blurFile.readFloatLE(offset);

  /***************
   * z values
   *
   */

  offset += bytesPerNumber;
  const z = file.readFloatLE(offset);
  const blur_z = blurFile.readFloatLE(offset);

  result.coordinates.push([x, y]);
  result.x_coordinates.push(x);
  result.y_coordinates.push(y);
  result.z_coordinates.push(z);

  // velocities
  result.dx.push(blur_x);
  result.dy.push(blur_y);
  result.dz.push(blur_z);

  if(blur_x !== 0.0){
    console.log('found blur data:', blur_x)
  }
  else if(blur_y !== 0.0){
    console.log('found blur data:', blur_y)
  }
  else if(blur_z !== 0.0){
    console.log('found blur data:', blur_z)
  }else{
    // console.log('no blur data found')
  }

  // Wave height
  result.height.push(z);
  vertices.push({
    x,
    y,
    z,
    dx: blur_x,
    dy: blur_y,
    dz: blur_z,
  });
}
console.log("done with ", fileName);
parentPort.postMessage({ result });
