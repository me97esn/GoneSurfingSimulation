const fs = require("fs");
const path = require("path");

const flip_fluid_cache_folder = "/ssd3/flip_fluid_cache/";
const source_folder_name = "flip_fluid_cache_5";

const { workerData, parentPort } = require("worker_threads");
const { fileName } = workerData;

const source_folder = path.join(flip_fluid_cache_folder, source_folder_name);
const bakefiles_folder = path.join(source_folder, "bakefiles");

const result = {
  coordinates: [],
  x_coordinates: [],
  y_coordinates: [],
  z_coordinates: [],
  x_values: [],
  y_values: [],
  z_values: [],
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
  result.x_values.push(blur_x);
  result.y_values.push(blur_y);
  result.z_values.push(blur_z);

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

// read triangels to calculate normals
offset += bytesPerNumber;
const numberOfTriangles = file.readUInt32LE(offset);
for (let i = 0; i < numberOfTriangles; i++) {
  offset += bytesPerNumber;
  const a = file.readUInt32LE(offset);
  offset += bytesPerNumber;
  const b = file.readUInt32LE(offset);
  offset += bytesPerNumber;
  const c = file.readUInt32LE(offset);
  const vertex_a = vertices[a];
  const vertex_b = vertices[b];
  const vertex_c = vertices[c];
  // TODO: calculate the normal and store it in the result
  //console.log("a,b,c", a, b, c);
  //console.log("vertex_a", vertex_a);
  //console.log("vertex_b", vertex_b);
  //console.log("vertex_c", vertex_c);
}
console.log("done with ", fileName);
parentPort.postMessage({ result });
