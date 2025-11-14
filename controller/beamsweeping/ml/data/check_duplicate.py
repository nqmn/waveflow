import pandas as pd

df = pd.read_csv("beam_dataset.csv")

# check duplicates based on all geometry columns
dups = df.duplicated(subset=[
    'ap_x','ap_y','ap_z',
    'ris_x','ris_y','ris_z',
    'ue_x','ue_y','ue_z'
]).sum()

print("Exact duplicate geometries:", dups)
