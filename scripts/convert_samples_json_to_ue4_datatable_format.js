/**
 * Convert wave_samples.json to height_samples_struct.json format for Unreal Engine.
 *
 * Usage:
 *   node convert_samples_json_to_ue4_datatable_format.js <source.json> <output.json> <output_metadata.json> [multiplier]
 *
 * Example:
 *   node convert_samples_json_to_ue4_datatable_format.js \
 *     /hdd/gone_surfing_exports/medium_wave_left/wave_samples.json \
 *     /hdd/gone_surfing_exports/medium_wave_left/height_samples_struct.json \
 *     /hdd/gone_surfing_exports/medium_wave_left/height_samples_struct_metadata.json \
 *     100
 */
const fs = require("fs");

const [, , sourceFileURL, resultFileUri, resultFileMetadataUri, _multiplier] =
  process.argv;

if (!sourceFileURL || !resultFileUri || !resultFileMetadataUri) {
  console.error("Usage: node convert_samples_json_to_ue4_datatable_format.js <source.json> <output.json> <output_metadata.json> [multiplier]");
  process.exit(1);
}

const content = fs.readFileSync(sourceFileURL, {
  encoding: "utf8",
  flag: "r",
});

const sourceData = JSON.parse(content);
const result = [];
const multiplier = parseInt(_multiplier) || 100;

const metadata = [
  {
    Name: "Metadata",
    step_size: sourceData.step_size,
    start_trace_x: sourceData.start_trace_x,
    start_trace_y: sourceData.start_trace_y,
    len_x: sourceData.x_length / sourceData.step_size,
    len_y: sourceData.y_length / sourceData.step_size,
    multiplier,
  },
];

console.log(`Converting ${sourceFileURL}`);
console.log(`  Start frame: ${sourceData.start_frame}`);
console.log(`  End frame: ${sourceData.end_frame}`);
console.log(`  Step size: ${sourceData.step_size}`);
console.log(`  Multiplier: ${multiplier}`);
console.log(`  Grid: ${metadata[0].len_x} x ${metadata[0].len_y}`);

let frameIndex = 0;
for (let samples2darray of sourceData.samples) {
  const values = [];
  result.push({
    Name: `Frame_${frameIndex + sourceData.start_frame}`,
    f: values,
  });

  for (let row of samples2darray) {
    const encapsulatingObj = {
      arr: row.map((value) => Math.round(value * multiplier)),
    };
    values.push(encapsulatingObj);
  }

  frameIndex++;
}

console.log(`  Processed ${frameIndex} frames`);

console.log(`Writing to ${resultFileUri}`);
fs.writeFileSync(resultFileUri, JSON.stringify(result), {
  encoding: "utf8",
  flag: "w",
});

console.log(`Writing to ${resultFileMetadataUri}`);
fs.writeFileSync(resultFileMetadataUri, JSON.stringify(metadata, null, 2), {
  encoding: "utf8",
  flag: "w",
});

console.log(`Done!`);
