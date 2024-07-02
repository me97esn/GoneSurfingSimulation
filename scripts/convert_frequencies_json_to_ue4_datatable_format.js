const fs = require("fs");
const [, , sourceFileURL, resultFileUri] = process.argv;
const content = fs.readFileSync(sourceFileURL, {
  encoding: "utf8",
  flag: "r",
});
const sourceData = JSON.parse(content);
console.log(sourceData.frequencies_per_frame.length);
const result = [];
let i = 0;
for (let frequency2darray in sourceData.frequencies_per_frame) {
  result.push({
    Name: `Frame_${i}`,
    step_size: sourceData.step_size,
    number_of_frequencies_to_include:
      sourceData.number_of_frequencies_to_include,
    number_of_rows_to_include: sourceData.number_of_rows_to_include,
    len_x: sourceData.len_x,
    len_y: sourceData.len_y,
  });
  i++;
}

console.log(result);
