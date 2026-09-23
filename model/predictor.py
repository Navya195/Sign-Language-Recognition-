"""
SignAI — Real-Time ML Predictor Engine
Loads trained classification model and predicts sign gestures from hand landmarks.
"""

import os
import sys
import joblib
import numpy as np

# Add project root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from utils.landmark_utils import extract_and_normalize_landmarks

class SignAIPredictor:
    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.load_model()

    def load_model(self):
        """Loads trained model or triggers training pipeline if missing."""
        if not os.path.exists(Config.MODEL_PATH) or not os.path.exists(Config.ENCODER_PATH):
            print("Model file not found. Running training pipeline...")
            from model.train_model import train_and_evaluate
            train_and_evaluate()

        try:
            self.model = joblib.load(Config.MODEL_PATH)
            self.label_encoder = joblib.load(Config.ENCODER_PATH)
            print("Trained SignAI ML Model loaded successfully.")
        except Exception as e:
            print("Failed to load model.")

    def predict(self, landmarks_list):
        """
        Performs real ML prediction on 21 MediaPipe hand landmarks.
        Returns prediction dictionary with true class probability confidence.
        """
        if self.model is None:
            self.load_model()

        feature_vector = extract_and_normalize_landmarks(landmarks_list)
        if feature_vector is None:
            return {'status': 'error', 'message': 'Invalid landmarks payload'}

        # Reshape for single sample prediction (1, 63)
        X = feature_vector.reshape(1, -1)
        
        # Real ML prediction & probability distribution
        predicted_class_encoded = self.model.predict(X)[0]
        original_class_id = int(self.label_encoder.inverse_transform([predicted_class_encoded])[0])
        
        probabilities = self.model.predict_proba(X)[0]
        max_prob = float(np.max(probabilities))

        gesture_meta = Config.GESTURES.get(original_class_id, {
            'name': 'Unknown', 'code': '?', 'emoji': '❓', 'description': 'Unrecognized gesture'
        })

        return {
            'status': 'success',
            'gesture_id': original_class_id,
            'name': gesture_meta['name'],
            'code': gesture_meta['code'],
            'emoji': gesture_meta['emoji'],
            'description': gesture_meta.get('description', ''),
            'confidence': round(max_prob, 4),
            'confidence_pct': int(max_prob * 100),
            'probabilities': {
                Config.GESTURES[int(cls)]['name']: round(float(prob), 4)
                for cls, prob in zip(self.label_encoder.classes_, probabilities)
            }
        }

predictor = SignAIPredictor()
