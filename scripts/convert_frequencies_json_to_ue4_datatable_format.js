const fs = require("fs");
const [, , sourceFileURL, resultFileUri] = process.argv;
const content = fs.readFileSync(sourceFileURL, {
  encoding: "utf8",
  flag: "r",
});
const sourceData = JSON.parse(content);
const result = [];
let i = 0;
for (let frequency2darray of sourceData.frequencies_per_frame) {
  const frequencies = [];
  result.push({
    Name: `Frame_${i + sourceData.start_frame}`,
    step: sourceData.step_size,
    // Number of frequencies to include
    num_of_f: sourceData.number_of_frequencies_to_include,
    // Number of rows to include
    num_of_r: sourceData.number_of_rows_to_include,
    l_x: sourceData.len_x,
    l_y: sourceData.len_y,
    // frequencies this frame
    f: frequencies,
  });
  for (let row of frequency2darray) {
    const encapsulatingObj = {
      arr: row.map(([real, imaginary]) => ({ re: real, im: imaginary })),
    };
    frequencies.push(encapsulatingObj);
  }

  i++;
}

console.log(`Writing to ${resultFileUri}`);
fs.writeFileSync(resultFileUri, JSON.stringify(result, null, 2), {
  encoding: "utf8",
  flag: "w",
});
