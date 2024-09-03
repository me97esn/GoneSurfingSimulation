const fs = require("fs");
const [, , sourceFileURL, resultFileUri, resultFileMetadataUri] = process.argv;
const content = fs.readFileSync(sourceFileURL, {
  encoding: "utf8",
  flag: "r",
});
const sourceData = JSON.parse(content);
const result = [];
let i = 0;

const metadata = [
  {
    Name: "Metadata",
    step_size: sourceData.step_size,
    number_of_frequencies_to_include:
      sourceData.number_of_frequencies_to_include,
    number_of_rows_to_include: sourceData.number_of_rows_to_include,
    start_trace_x: sourceData.start_trace_x,
    start_trace_y: sourceData.start_trace_y,
    len_x: sourceData.len_x,
    len_y: sourceData.len_y,
  },
];

console.log(sourceData.frequencies_per_frame);

for (let frequency2darray of sourceData.frequencies_per_frame) {
  const frequencies = [];
  result.push({
    Name: `Frame_${i + sourceData.start_frame}`,
    f: frequencies,
  });
  for (let row of frequency2darray) {
    const encapsulatingObj = {
      arr: row.map(([real, imaginary]) => ({
        re: real,
        im: imaginary,
      })),
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
console.log(`Writing to ${resultFileMetadataUri}`);
fs.writeFileSync(resultFileMetadataUri, JSON.stringify(metadata, null, 2), {
  encoding: "utf8",
  flag: "w",
});
console.log(`Done!`);
