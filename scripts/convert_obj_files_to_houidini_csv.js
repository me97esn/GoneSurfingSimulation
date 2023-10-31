const fs = require('fs')
const resultFileName = '/ssd2/git/gone-surfing-ue4-2/GoneSurfing/data/medium_left_white_water_foam.hcsv'
const path = require('path')

const dir = '/hdd/gone surfing exports/medium wave left/white_water'

fs.unlinkSync(resultFileName);
fs.writeFileSync(resultFileName,'Px,Py,Pz,id,time,type,life\n')
const fps = 1 
let i = 0 
const files = fs.readdirSync(dir)
let doWrite = true
for(const fileName of files){
  if(fileName.match(/.*obj/ ) ){
    console.log(fileName)
    const [timeStr] = fileName.match(/(\d+)/g)
    const time = parseInt(timeStr) /fps

    const content = fs.readFileSync(path.join(dir, fileName),
      {encoding:'utf8', flag:'r'})
    const data = content.split('\n') 
    for(line of data){
      doWrite = !doWrite
      
      if(line.match(/v .*/) && doWrite){
        i++
        const [,x,y,z] = line.split(' ')
        const str = `${x},${y},${z},${i},${time },${time},1.0\n`  
        fs.appendFileSync(resultFileName,str)
      }
    }
  }
}
