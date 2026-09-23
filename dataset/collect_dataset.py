"""
SignAI — Dataset Generation & Preprocessing Pipeline
Generates preprocessed hand gesture landmark feature dataset (63 3D keypoint features per sample).
"""

import os
import sys
import csv
import numpy as np

# Add project root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from utils.landmark_utils import generate_synthetic_landmarks_for_gesture

def build_dataset(samples_per_class=200):
    os.makedirs(Config.DATASET_DIR, exist_ok=True)
    csv_path = Config.DATASET_CSV
    
    headers = []
    for i in range(21):
        headers.extend([f'x{i}', f'y{i}', f'z{i}'])
    headers.extend(['label', 'gesture_name'])

    total_rows = 0
    with open(csv_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for gesture_id, meta in Config.GESTURES.items():
            print(f"Generating samples for Class {gesture_id}: {meta['name']}...")
            for sample_idx in range(samples_per_class):
                # Generate realistic 63-feature landmark vector with natural variance
                features = generate_synthetic_landmarks_for_gesture(gesture_id)
                # Add gaussian noise for robustness
                noise = np.random.normal(0, 0.02, size=features.shape)
                augmented_features = features + noise
                
                row = list(augmented_features) + [gesture_id, meta['name']]
                writer.writerow(row)
                total_rows += 1

    print("\nDataset generated successfully.")
    print(f"Total Samples: {total_rows} across {len(Config.GESTURES)} classes.")
    return csv_path

if __name__ == '__main__':
    build_dataset()
