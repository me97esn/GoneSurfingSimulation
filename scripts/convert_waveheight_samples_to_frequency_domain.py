import numpy as np
import json

f = open('wave_samples.json')
samples = json.load(f)

output_filename_freqs = "wave_frequencies_subset.json"
output_filepath_freqs = os.path.join(output_directory, output_filename_freqs)
file_freqs = open(output_filepath_freqs, "w")
number_of_frequencies_to_include = 10
frequencies_result = {"number_of_frequencies_to_include": number_of_frequencies_to_include }

# This is the number of low frequency frequencies, and high frequency frequencies to include. They are by coincidence the same number.
number_of_freqs = 15
frequencies_all_frames = [np.fft.fftn(frame) for frame in samples]
filtered_frequencies_all_frames = [np.array([[z for zi, z in enumerate(arr) if zi < number_of_freqs or zi >= len(arr)-number_of_freqs] for arr in frame_frequencies]).toList() for frame_frequencies in frequencies_all_frames]
frequencies_result["frequencies_per_frame"] = filtered_frequencies_all_frames
file_freqs.write(json.dumps(frequencies_result))
file_freqs.close()
