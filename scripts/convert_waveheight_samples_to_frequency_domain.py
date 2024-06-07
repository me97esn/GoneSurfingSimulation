import numpy as np
import json
import os
from json import JSONEncoder

class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif np.iscomplexobj(obj):
            return [np.real(obj), np.imag(obj)]
        return JSONEncoder.default(self, obj)

directory = "/home/emil/workspace/GoneSurfingScripts"
filename = "wave_samples.json"
filename = os.path.join(directory, filename)
f = open(filename, "r")
samples = json.load(f)

output_filename_freqs = "wave_frequencies_subset.json"
output_filepath_freqs = os.path.join(directory, output_filename_freqs)
file_freqs = open(output_filepath_freqs, "w")
number_of_frequencies_to_include = 10
frequencies_result = {"number_of_frequencies_to_include": number_of_frequencies_to_include, "len_x": len(samples[0]), "len_y": len(samples[0][0])}

# This is the number of low frequency frequencies, and high frequency frequencies to include. They are by coincidence the same number.
frequencies_all_frames = [np.fft.fftn(frame) for frame in samples]
filtered_frequencies_all_frames = [np.array([[z for zi, z in enumerate(arr) if zi < number_of_frequencies_to_include or zi >= len(arr)-number_of_frequencies_to_include ] for arr in frame_frequencies]) for frame_frequencies in frequencies_all_frames]
frequencies_result["frequencies_per_frame"] = filtered_frequencies_all_frames
file_freqs.write(json.dumps(frequencies_result, cls=NumpyArrayEncoder))
file_freqs.close()
