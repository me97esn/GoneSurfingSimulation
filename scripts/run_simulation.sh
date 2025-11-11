#!/bin/bash

while true; do
    echo "Starting Blender simulation..."
    /snap/bin/blender ../3dmodels/breaking_waves_beach_break_2.blend --python run_simulation.py

    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo "Simulation completed successfully. Exiting."
        break
    else
        echo "Simulation crashed with exit code $exit_code. Restarting in 5 seconds..."
        sleep 5
    fi
done
