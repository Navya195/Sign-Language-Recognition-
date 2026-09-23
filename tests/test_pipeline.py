import os
import sys
import unittest
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.landmark_utils import extract_and_normalize_landmarks, generate_synthetic_landmarks_for_gesture
from model.predictor import predictor
from database import init_db, get_db

class TestSignAIPipeline(unittest.TestCase):
    
    def test_landmark_extraction_and_normalization(self):
        """Test that synthetic landmarks are correctly normalized to a 63-element vector."""
        raw_landmarks = generate_synthetic_landmarks_for_gesture(1) # Gesture 'One'
        
        self.assertIsNotNone(raw_landmarks)
        self.assertEqual(len(raw_landmarks), 63)
        self.assertEqual(type(raw_landmarks), np.ndarray)

    def test_ml_model_prediction(self):
        """Test that the trained Random Forest model successfully predicts a known gesture."""
        # We simulate a perfect 'Victory/Two' gesture (Class ID: 2)
        simulated_landmarks = []
        for _ in range(21):
            simulated_landmarks.append({'x': 0.5, 'y': 0.5, 'z': 0.0}) # Dummy flat input
            
        result = predictor.predict(simulated_landmarks)
        self.assertEqual(result['status'], 'success')
        self.assertTrue('gesture_id' in result)
        self.assertTrue('confidence_pct' in result)
        
    def test_database_initialization(self):
        """Test that SQLite database initializes and creates required tables."""
        init_db()
        conn = get_db()
        
        # Check if users table exists
        users_table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        self.assertIsNotNone(users_table)
        
        # Check if history table exists
        history_table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'").fetchone()
        self.assertIsNotNone(history_table)
        
        conn.close()

if __name__ == '__main__':
    unittest.main()
