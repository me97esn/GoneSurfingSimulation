#! /bin/bash
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_0.json 752 800 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_3b.json  801 850 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_1.json 851 900 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_3c.json 901 950 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_1b.json 951 1000 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_4.json 1001 1050 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_2.json 1051 1100 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_4b.json 1101 1150 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_2b.json 1151 1200 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_4c.json 1201 1250 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_3.json 1251 1300 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_4d.json 1301 1350 &

# The rest here is just to create empty force files, to make it easier to import different number of files into ue4
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_5.json 0 1 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_5a.json 0 1 &
node -max-old-space-size=32768 create_water_velocity_datatable.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_water_velocities_5b.json 0 1
