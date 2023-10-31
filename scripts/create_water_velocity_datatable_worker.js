const fs = require('fs')
const path = require('path')

const flip_fluid_cache_folder = '/ssd3/flip_fluid_cache/'
const source_folder_name = 'flip_fluid_cache_5'

const { workerData, parentPort } = require('worker_threads')
const {fileName} = workerData

const resolution = 1
// TODO: use param instead
const minVectorLength = Math.pow(0.075,2)
const source_folder = path.join(flip_fluid_cache_folder, source_folder_name)
const bakefiles_folder = path.join(source_folder, 'bakefiles')


const match = fileName.match(/^(\d+).bobj/)
const [,timeStr] = match 
const time = parseFloat(timeStr)

const result = []
const file  = fs.readFileSync(path.join(bakefiles_folder, fileName), null)
const blurFile= fs.readFileSync(path.join(bakefiles_folder, `blur${fileName}`), null)
const numberOfVertices = file.readUInt32LE()
const bytesPerNumber = 4
let offset = 0

for(let i = 0; i < numberOfVertices; i++){

  // if(i === 100){
  //   break
  // }

  /***************
   * x values 
   *
   */

  offset += bytesPerNumber
  const x =  file.readFloatLE(offset)  
  const blur_x =  blurFile.readFloatLE(offset)  
  const ue4Y = x
  const ue4BlurY = blur_x

  /***************
   * y values 
   *
   */

  offset += bytesPerNumber
  const y =  file.readFloatLE(offset)  
  const blur_y =  blurFile.readFloatLE(offset)  
  const ue4Z = y
  const ue4BlurZ = blur_y

  /***************
   * z values 
   *
   */

  offset += bytesPerNumber
  const z =  file.readFloatLE(offset)  
  const blur_z =  blurFile.readFloatLE(offset)  
  const ue4X = z
  const ue4BlurX = blur_z

  /**
   * The current simulation has a lot of forces on the shore, which can be ignored
   */
  if(ue4Z < -205){
    // Ignore forces on the beach
    continue
  }

  /***************
   * Create the data
   *
   */
  const floorY = Math.floor(ue4Y*resolution)/resolution
  const floorZ = Math.floor(ue4Z*resolution)/resolution


  const key = `F${parseFloat(timeStr)}Y${floorY.toFixed(0)}Z${floorZ.toFixed(0)}`
  let row = result.find(obj => obj.Name === key)
 
  // Only store vertices where the forces have a minimum size
  const lengthSquared = Math.pow(ue4BlurX, 2) + Math.pow(ue4BlurY, 2) + Math.pow(ue4BlurZ, 2)
  // if(!key.startsWith('F350Y-44') ){
  //   continue
  // }
  if(lengthSquared < minVectorLength){
    continue
  }

  if(!row){
    row = {
      Name: key,
      values : []
    }
    result.push(row)
  }  
  
  // Round and multiply every number to reduce data
  const roundedValues = [ue4X, ue4Y, ue4Z, ue4BlurX, ue4BlurY, ue4BlurZ].map(i => Math.round(i * 1000))  
  // const roundedValues = [ue4X, ue4Y, ue4Z, ue4BlurX, ue4BlurY, ue4BlurZ].map(i => i)
  row.values.push({loc: roundedValues})
}
parentPort.postMessage({ result })
