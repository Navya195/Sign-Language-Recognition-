"""
SignAI — Machine Learning Model Training & Evaluation Pipeline
Trains Random Forest & Neural Network classifiers on 63-landmark feature dataset,
evaluates accuracy/precision metrics, and exports trained model.
"""

import os
import sys
import joblib
import numpy as np

# Add project root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

def train_and_evaluate():
    csv_path = Config.DATASET_CSV
    if not os.path.exists(csv_path):
        print("Dataset not found. Running dataset generator first...")
        from dataset.collect_dataset import build_dataset
        build_dataset()

    print("Loading dataset from CSV...")
    data = np.genfromtxt(csv_path, delimiter=',', skip_header=1, dtype=str)
    
    X = data[:, :63].astype(np.float32)
    y_labels = data[:, 63].astype(int)
    
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_labels)

    # Train/Test Split (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"Training Data: {X_train.shape[0]} samples | Test Data: {X_test.shape[0]} samples")

    # 1. Train Random Forest Classifier
    rf_model = RandomForestClassifier(
        n_estimators=100, max_depth=15, random_state=42
    )
    rf_model.fit(X_train, y_train)

    # 2. Evaluate Model
    y_pred = rf_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print("\n" + "="*60)
    print(f"MODEL TRAINING EVALUATION RESULT")
    print("="*60)
    print(f"Overall Model Accuracy: {accuracy * 100:.2f}%\n")
    
    gesture_names = [Config.GESTURES[cls]['name'] for cls in label_encoder.classes_]
    print(classification_report(y_test, y_pred, target_names=gesture_names))

    # Save Model & Encoder
    os.makedirs(Config.MODEL_DIR, exist_ok=True)
    joblib.dump(rf_model, Config.MODEL_PATH)
    joblib.dump(label_encoder, Config.ENCODER_PATH)

    print("\nModel saved successfully.")
    print("Label Encoder saved successfully.")
    
    return accuracy

if __name__ == '__main__':
    train_and_evaluate()
