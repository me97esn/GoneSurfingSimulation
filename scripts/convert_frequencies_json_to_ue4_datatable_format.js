const fs = require("fs");
const [, , sourceFileURL, resultFileUri] = process.argv;
const content = fs.readFileSync(sourceFileURL, {
  encoding: "utf8",
  flag: "r",
});
const data = JSON.parse(content);
