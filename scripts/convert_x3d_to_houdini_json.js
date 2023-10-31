const convert = require('xml-js')
const fs = require('fs')
const dir = '/hdd/gone_surfing_exports/medium_wave_left/waves_display'
const path = require('path')

const [,,resultFileUri, startWriteParticlePercent, endWriteParticlePercent] = process.argv


const startFrame = 150 

let i = 0 
const files = fs.readdirSync(dir)
const frames = []
let num_samples = 0
let num_frames = 0
let max_num_points= 0

let doWrite = true
const fps = 0.041667  

// A pseudo random number generator
//https://svijaykoushik.github.io/blog/2019/10/04/three-awesome-ways-to-generate-random-number-in-javascript/ 
// r = randomGenerator() 
// const randomValue = r.next().value 
function* randomGenerator(){
  const seed = 44 
  let X = seed
  const a = 1664525 
  const c = 1013904223 
  const m = Math.pow(2,32) 
  function linearCongruentialGenerator(){
    X = (a * X + c) % m;
    return X;
  }
  while(true){
    yield linearCongruentialGenerator()/m
  }
}
const random = randomGenerator()


for(const fileName of files){
  if(fileName.match(/.*x3d$/ ) ){
    console.log(fileName)
    let num_points_this_frame = 0
    const frame_data = []


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

        const randomValue = random.next().value 
        if(startWriteParticlePercent <= randomValue && randomValue <= endWriteParticlePercent){
          // This is used to split the result into multiple files

          num_samples++
          num_points_this_frame++
          const particleId = num_samples
          const life = 1.01
          frame_data.push([particleId,life,...coordsAndNormals])
        }
      }
    }

    const distance = ([x1, y1, z1],[x2, y2, z2])=>{
      // d = ((x2 - x1)2 + (y2 - y1)2 + (z2 - z1)2)1/2      
      return Math.sqrt(Math.pow( x2 - x1, 2 ) +  Math.pow( y2 -y1 , 2 ) +  Math.pow( z2 - z1, 2 ) ) 
    }

    const frame_data_with_scale = frame_data.map(([particleId,life,xPos, yPos, zPos, xNormal, yNormal, zNormal]) => {
      const distanceToAllParticles = frame_data.map(([,,x2Pos, y2Pos, z2Pos ]) => distance([xPos, yPos,zPos],[x2Pos, y2Pos, z2Pos]) )
      // Note: every particle is included when checking distance, so the least distance is always 0. 
      const leastDistance = distanceToAllParticles.sort((a,b) => a-b)[1]
      const pscale = Math.round(leastDistance * 10000)/10000 // Make sure that the number isn't bigger then a float
      // console.log(pscale)
      return [particleId,life,xPos, yPos, zPos, xNormal, yNormal, zNormal, pscale] 
    } )

    frames.push({number:num_frames+1, time, num_points:num_points_this_frame, frame_data:frame_data_with_scale })
    max_num_points = max_num_points >= num_points_this_frame ? max_num_points: num_points_this_frame 
    num_frames++
    console.log('frames', num_frames)
  }
  // if(num_frames > 50){
  //   break
  // }
}

const attrib_name = ["id", "life","P", "N", "pscale"]
const result = { 
  header: {
    version: "1.0", 
    num_samples, 
    num_frames,
    num_points: num_samples, 
    num_attrib: attrib_name.length, 
    attrib_name, 
    attrib_size: [1,1,3,3,1], 
    attrib_data_type: ["l","f","f", 'f','f','f','f','f','f'], 
    data_type: "linear"
  }, 
  cache_data: {
    frames 
  }
}
console.log('Writing the file...', resultFileUri)
fs.writeFileSync(resultFileUri,JSON.stringify(result))
console.log('Done.')
