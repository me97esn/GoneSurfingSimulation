const convert = require('xml-js')
const fs = require('fs')
const path = require('path')

const [,,dir, resultFileUri ] = process.argv


const startFrame = 0 
let i = 0 
const files = fs.readdirSync(dir)
const fps = 0.041667  
const resolution = 1 // increase this to get more groups, with less vertices per group. 0.1 will lead to keys of the type F0Y120Z30, 1 will lead to F0Y122Z34, 10 will lead to F0Y122.3Z34.0 and so on

// A pseudo random number generator
//https://svijaykoushik.github.io/blog/2019/10/04/three-awesome-ways-to-generate-random-number-in-javascript/ 
// r = randomGenerator() 
// const randomValue = r.next().value 
// function* randomGenerator(){
//   const seed = 44 
//   let X = seed
//   const a = 1664525 
//   const c = 1013904223 
//   const m = Math.pow(2,32) 
//   function linearCongruentialGenerator(){
//     X = (a * X + c) % m;
//     return X;
//   }
//   while(true){
//     yield linearCongruentialGenerator()/m
//   }
// }
// const random = randomGenerator()

for(const fileName of files){
  const result = fs.existsSync(resultFileUri) && JSON.parse(fs.readFileSync(resultFileUri)) || []
  if(fileName.match(/.*x3d$/ ) ){
    console.log(fileName)

    const [timeStr] = fileName.match(/(\d+)\./g)
    const time = (parseFloat(timeStr) - startFrame ) * fps
    console.log(time)
    const content = fs.readFileSync(path.join(dir, fileName),
      {encoding:'utf8', flag:'r'})
    const {elements:rootElements} = convert.xml2js(content)
    const {elements: level1elements} = rootElements.find(el => el.elements)
    const {elements: level2elements} = level1elements.find(el => el.name === 'Scene')
    const {elements: level3elements} = level2elements.find(el => el.name === 'Transform')
    const {elements: level4elements} = level3elements.find(el => el.name === 'Transform')
    const {elements: level5elements} = level4elements.find(el => el.name === 'Group')
    const {elements: level6elements} = level5elements.find(el => el.name === 'Shape')
    const {elements: level7elements} = level6elements.find(el => el.name === 'IndexedFaceSet')
    const {attributes:{vector:normalsStr}} = level7elements.find(el => el.name === 'Normal')
    const {attributes:{point:coordinatesStr}} = level7elements.find(el => el.name === 'Coordinate')
    const normals = normalsStr.trim().split(' ')
    const coordinates = coordinatesStr.trim().split(' ')

    while(normals.length >= 3 && coordinates.length >= 3){
      const coordsAndNormals = [coordinates.pop(),
        coordinates.pop(),
        coordinates.pop(),
        normals.pop(),
        normals.pop(),
        normals.pop()].map(numStr => Number.parseFloat(numStr))

      // Include every vertice for now
      // {       
      // Only include vertices pointing upwards, but z isn't up.
      // Also: A few single lying vertices will have close to zero up normal, but should be skipped. Otherwise noice will occur
      // 
      // console.log(coordsAndNormals[3], coordsAndNormals[4], coordsAndNormals[5])
      if(coordsAndNormals[3]> 0){

        // const randomValue = random.next().value 

        // if(startWriteParticlePercent <= randomValue && randomValue <= endWriteParticlePercent){
        // Write every vertice, no randomization for now
        { 
          // Y: from/to the shore
          // X: along the shore
          // Z: up/down
          const [X,Y,Z,NX,NY,NZ] = coordsAndNormals
          //const floorX = Math.floor(X*resolution)/resolution
          const floorY = Math.floor(Y*resolution)/resolution
          const floorZ = Math.floor(Z*resolution)/resolution
          const key = `F${parseFloat(timeStr)}Y${floorY}Z${floorZ}`
          let row = result.find(obj => obj.Name === key)

          if(!row){
            row = {
              Name: key,
              values: []
            }
            result.push(row)
          }  
          // Round and multiply, only to reduce data
          const roundedValues = [X,Y,Z,NX,NY,NZ].map(i => Math.round(i*1000))
          row.values.push({loc: roundedValues})
          
        }
      }
    }

  }
  /**
   * Replace the content of the result file after each written file
   * and remove the processed file. This makes it possible to continue on next run where the last run ended.
   */
  // First write the result
  fs.writeFileSync(resultFileUri,JSON.stringify(result,null,2))
  // then remove the processed file. This order is important, otherwise I might remove the 3d file and quit before the result is persisted!
  
  fs.rmSync(path.join(dir, fileName))
  console.log(`Removed the file ${fileName} after successfully processing it.`)
}


console.log('Done.')
