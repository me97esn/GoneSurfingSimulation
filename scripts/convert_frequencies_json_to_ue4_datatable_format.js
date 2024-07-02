const fs = require("fs");
const [, , sourceFileURL, resultFileUri] = process.argv;
const content = fs.readFileSync(sourceFileURL, {
  encoding: "utf8",
  flag: "r",
});
const sourceData = JSON.parse(content);
const result = [];
let i = 0;
// TODO: should the frames start with 0 or 1?
for (let frequency2darray of sourceData.frequencies_per_frame) {
  const frequencies = [];
  result.push({
    Name: `Frame_${i}`,
    step_size: sourceData.step_size,
    number_of_frequencies_to_include:
      sourceData.number_of_frequencies_to_include,
    number_of_rows_to_include: sourceData.number_of_rows_to_include,
    len_x: sourceData.len_x,
    len_y: sourceData.len_y,
    frequencies_this_frame: frequencies,
  });
  for (let row of frequency2darray) {
    const encapsulatingObj = {
      arr: row.map(([real, imaginary]) => ({ real, imaginary })),
    };
    frequencies.push(encapsulatingObj);
  }

  i++;
  break;
}

console.log(JSON.stringify(result, null, 2));
