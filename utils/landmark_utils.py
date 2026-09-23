"""
SignAI — Landmark Normalization and Feature Extraction Utilities
Processes MediaPipe 21 3D hand keypoints into scale & translation invariant feature vectors.
"""

import numpy as np

def extract_and_normalize_landmarks(landmarks_list):
    """
    Given a list of 21 landmark dicts or tuples [{'x':..., 'y':..., 'z':...}],
    converts to translation & scale invariant 63-element numpy array.
    """
    if landmarks_list is None or len(landmarks_list) < 21:
        return None

    coords = []
    for lm in landmarks_list:
        if isinstance(lm, dict):
            coords.append([lm.get('x', 0.0), lm.get('y', 0.0), lm.get('z', 0.0)])
        else:
            coords.append([lm[0], lm[1], lm[2] if len(lm) > 2 else 0.0])

    coords = np.array(coords, dtype=np.float32)

    # 1. Translation Invariance: Subtract Wrist (index 0) position
    wrist = coords[0].copy()
    coords = coords - wrist

    # 2. Scale Invariance: Divide by max Euclidean distance from wrist
    distances = np.linalg.norm(coords, axis=1)
    max_dist = np.max(distances)
    if max_dist > 1e-6:
        coords = coords / max_dist

    # Flatten into 63-dimensional feature vector [x0, y0, z0, x1, y1, z1, ...]
    return coords.flatten()

def generate_synthetic_landmarks_for_gesture(gesture_id):
    """
    Generates realistic 21-landmark 3D coordinate patterns for training/testing.
    """
    # Base hand skeleton template (wrist at 0,0,0)
    np.random.seed(42 + gesture_id * 7)
    base = np.zeros((21, 3), dtype=np.float32)

    # Thumb: 1-4
    # Index: 5-8
    # Middle: 9-12
    # Ring: 13-16
    # Pinky: 17-20

    # Finger extension patterns for gestures (0-21)
    extension_map = {
        0:  [0, 0, 0, 0, 0],     # Zero / Fist
        1:  [0, 1, 0, 0, 0],     # One
        2:  [0, 1, 1, 0, 0],     # Two / Victory
        3:  [0, 1, 1, 1, 0],     # Three
        4:  [0, 1, 1, 1, 1],     # Four
        5:  [1, 1, 1, 1, 1],     # Five / Open
        6:  [1, 0, 0, 0, 1],     # Six
        7:  [0, 0, 1, 1, 1],     # Seven
        8:  [1, 0, 1, 1, 1],     # Eight
        9:  [1, 1, 0, 1, 1],     # Nine
        10: [1, 0, 0, 0, 0],     # Letter A
        11: [0, 1, 1, 1, 1],     # Letter B
        12: [1, 1, 0, 0, 0],     # Letter C
        13: [0, 1, 0, 0, 0],     # Letter D
        14: [0, 0, 0, 0, 0],     # Letter E
        15: [0, 0, 1, 1, 1],     # Letter F
        16: [1, 1, 0, 0, 0],     # Letter G
        17: [1, 1, 1, 1, 1],     # Hello
        18: [0, 1, 1, 0, 0],     # Thanks
        19: [1, 0, 0, 0, 0],     # Yes
        20: [0, 1, 1, 0, 0],     # No
        21: [1, 1, 0, 0, 1]      # Love
    }

    ext = extension_map.get(gesture_id % 15, [1, 1, 1, 1, 1])

    # Build anatomical structure
    finger_angles = [-0.4, -0.15, 0.0, 0.15, 0.35]
    for finger_idx in range(5):
        angle = finger_angles[finger_idx]
        is_extended = ext[finger_idx]
        length_mult = 1.0 if is_extended else 0.3

        for joint in range(1, 5):
            idx = finger_idx * 4 + joint
            dist = joint * 0.25 * length_mult
            base[idx, 0] = dist * np.sin(angle) + np.random.normal(0, 0.01)
            base[idx, 1] = -dist * np.cos(angle) + np.random.normal(0, 0.01)
            base[idx, 2] = (joint * 0.05 if not is_extended else 0.0) + np.random.normal(0, 0.01)

    # Apply random 2D rotation (roll) to make model robust to hand tilt
    theta = np.random.uniform(-np.pi/4, np.pi/4) # +/- 45 degrees
    c, s = np.cos(theta), np.sin(theta)
    rot_matrix = np.array(((c, -s), (s, c)))
    
    for i in range(21):
        base[i, :2] = np.dot(rot_matrix, base[i, :2])

    return extract_and_normalize_landmarks(base)
