const fs = require('fs')
const path = require('path')
const dir = '/hdd/gone surfing exports/medium wave left/waves_display'

const fps = 0.041667  
let num_samples = 0
let num_frames = 0
let max_num_points= 0
const frames = []
const startFrame = 777 
const files = fs.readdirSync(dir)
const [,,resultFileUri, startWriteParticlePercent, endWriteParticlePercent] = process.argv

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
  if(fileName.match(/.*obj/ ) ){
    console.group(fileName)
    let num_points_this_frame = 0
    const frame_data = []
    const temp_frame_data = []
    const grouped_frame_data = {}
    const [timeStr] = fileName.match(/(\d+)\./g)
    const time = (parseFloat(timeStr) - startFrame ) * fps

    const content = fs.readFileSync(path.join(dir, fileName),
      {encoding:'utf8', flag:'r'})
    const data = content.split('\n') 
    for(line of data){
      if(line.match(/v .*/) ){
        // store the data, to later be grouped.
        const [,x,y,z] = line.split(' ')
        temp_frame_data.push([x,y,z])
      }
    }
   // We now have all of the coordinates for the vertices. Group them by x,y 
    for([x,y,z] of temp_frame_data){
      const roundAmount = 1 // Higher amount: more particles are written to file
      const roundedX = Math.round(x * roundAmount)
      const roundedY = Math.round(y * roundAmount)
      grouped_frame_data[`${roundedX},${roundedY}`] = grouped_frame_data[`${roundedX},${roundedY}`] || []

      grouped_frame_data[`${roundedX},${roundedY}`].push([x,y,z].map(valueStr => Number.parseFloat(valueStr))) 
    }

    // And only choose the top most vertex at all of the x/y positions
    const onlyTopVertices = Object.values(grouped_frame_data).map( coordsAtSamePosition =>  coordsAtSamePosition.sort((a,b) => b[2] - a[2])[0] ) 
    for([x,y,z] of onlyTopVertices){
      const randomValue = random.next().value 
      // It's possible to call this script with different values to split the vertices into different json files
      if(startWriteParticlePercent <= randomValue && randomValue <= endWriteParticlePercent){
        num_samples++
        num_points_this_frame++
        const particleId = num_samples
        const life = 1.01
        const nx = 0.5
        const ny = 0.5
        const nz = 1
        frame_data.push([particleId,life,x,y,z, nx, ny, nz])
        // break
      }
    }
    frames.push({number:num_frames+1, time, num_points:num_points_this_frame, frame_data })
    max_num_points = max_num_points >= num_points_this_frame ? max_num_points: num_points_this_frame 
    num_frames++
    console.groupEnd()
  }
  // if(num_frames >= 2){
  //   break
  // }
}
const attrib_name = ["id", "life","P", "N"]
const result = { 
  header: {
    version: "1.0", 
    num_samples, 
    num_frames,
    num_points: num_samples, 
    num_attrib: attrib_name.length, 
    attrib_name, 
    attrib_size: [1,1,3,3], 
    attrib_data_type: ["l","f","f", 'f','f','f','f','f'], 
    data_type: "linear"
  }, 
  cache_data: {
    frames 
  }
}
console.log('Writing the file...', resultFileUri)
fs.writeFileSync(resultFileUri,JSON.stringify(result))
console.log('Done.')
