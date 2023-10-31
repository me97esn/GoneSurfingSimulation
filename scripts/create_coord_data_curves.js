const [,,ue4DataFileUri, resultYFileURI, resultZFileURI] = process.argv
const ue4DataFile = require(ue4DataFileUri)
const fs = require('fs')
const os = require("os")

const allYKeys = new Set()
const allZKeys = new Set()

function closest(goal, array){
  return array.reduce((prev, curr) => Math.abs(curr - goal) < Math.abs(prev - goal) ? curr : prev);
}

function sort(set){
  return Array.from(set).sort((a,b)=>a - b)
}
const framesData = []
for(const frame of ue4DataFile){

  const keyPairs = Object.keys(frame.GroupedLocations)
    .map(key => key.split(',').map(keyPart => parseFloat(keyPart)))
  const yKeys = new Set()
  const zKeys = new Set()
  keyPairs.forEach(([y,z])=> {
    allZKeys.add(z)
    allYKeys.add(y)
    yKeys.add(y)
    zKeys.add(z)
  })
  const yKeysSorted = sort(yKeys)
  const zKeysSorted = sort(zKeys)
  framesData.push({y: yKeysSorted, z: zKeysSorted, frame: frame.Name})
}
const allYKeysSorted = sort(allYKeys)
const allZKeysSorted = sort(allZKeys)
const yHeaderLine = `Name,${allYKeysSorted.join(',')}`
const zHeaderLine = `Name,${allZKeysSorted.join(',')}`

function writeYFileContent(){
  const contentLines = []
  for(const frameData of framesData){
    const filledValues = []

    for(const y of allYKeysSorted){
      filledValues.push(closest(y, frameData.y))
    }
    contentLines.push(`Frame:${frameData.frame},${filledValues.join(',')}`)
  }

  // Write the content of the y file
  fs.writeFileSync(resultYFileURI,yHeaderLine + os.EOL)
  for (const line of contentLines){
    fs.appendFileSync(resultYFileURI,line + os.EOL)
  }
}

function writeZFileContent(){
  const contentLines = []
  for(const frameData of framesData){
    const filledValues = []

    for(const z of allZKeysSorted){
      filledValues.push(closest(z, frameData.z))
    }
    contentLines.push(`Frame:${frameData.frame},${filledValues.join(',')}`)
  }

  // Write the content of the y file
  fs.writeFileSync(resultZFileURI,zHeaderLine+ os.EOL)
  for (const line of contentLines){
    fs.appendFileSync(resultZFileURI,line + os.EOL)
  }
}

writeYFileContent()
writeZFileContent()
