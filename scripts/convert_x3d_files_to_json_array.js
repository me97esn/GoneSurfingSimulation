const convert = require("xml-js");
const fs = require("fs");
const path = require("path");

const [, , dir, resultFileUri] = process.argv;

const files = fs.readdirSync(dir);
// NOTE: the order of the files are not in order. Don't use this for production data.
for (const fileName of files) {
  const row = [];
  const coords = [];
  if (fileName.match(/.*x3d$/)) {
    console.log(fileName);

    const content = fs.readFileSync(path.join(dir, fileName), {
      encoding: "utf8",
      flag: "r",
    });
    const { elements: rootElements } = convert.xml2js(content);
    const { elements: level1elements } = rootElements.find((el) => el.elements);
    const { elements: level2elements } = level1elements.find(
      (el) => el.name === "Scene"
    );
    const { elements: level3elements } = level2elements.find(
      (el) => el.name === "Transform"
    );
    const { elements: level4elements } = level3elements.find(
      (el) => el.name === "Transform"
    );
    const { elements: level5elements } = level4elements.find(
      (el) => el.name === "Group"
    );
    const { elements: level6elements } = level5elements.find(
      (el) => el.name === "Shape"
    );
    const { elements: level7elements } = level6elements.find(
      (el) => el.name === "IndexedFaceSet"
    );
    const {
      attributes: { vector: normalsStr },
    } = level7elements.find((el) => el.name === "Normal");
    const {
      attributes: { point: coordinatesStr },
    } = level7elements.find((el) => el.name === "Coordinate");
    const normals = normalsStr.trim().split(" ");
    const coordinates = coordinatesStr.trim().split(" ");

    while (normals.length >= 3 && coordinates.length >= 3) {
      const coordsAndNormals = [
        coordinates.pop(),
        coordinates.pop(),
        coordinates.pop(),
        normals.pop(),
        normals.pop(),
        normals.pop(),
      ].map((numStr) => Number.parseFloat(numStr));

      // if (coordsAndNormals[3] > 0)
      {
        {
          // TODO: sort the vertices
          const [X, Y, Z, NX, NY, NZ] = coordsAndNormals;
          const coord = { X, Y, Z };

          console.log(
            `X: ${X}, Y: ${Y}, Z: ${Z}, NX: ${NX}, NY: ${NY}, NZ: ${NZ}`
          );
          // row.push(X);
          coords.push(coord);
        }
      }
    }
  }
  const result = coords.sort((a, b) => a.Y - b.Y).map((coord) => coord.X);

  /**
   * Replace the content of the result file after each written file
   * and remove the processed file. This makes it possible to continue on next run where the last run ended.
   */
  // First write the result
  fs.writeFileSync(resultFileUri, JSON.stringify(result, null, 2));
  // then remove the processed file. This order is important, otherwise I might remove the 3d file and quit before the result is persisted!

  // fs.rmSync(path.join(dir, fileName));
  // console.log(`Removed the file ${fileName} after successfully processing it.`);
}

console.log("Done.");
