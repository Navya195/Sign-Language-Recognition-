import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'signai-super-secret-key-2026')
    PORT = int(os.environ.get('PORT', 5500))
    DEBUG = False
    
    # Dataset & Model paths
    DATASET_DIR = os.path.join(BASE_DIR, 'dataset')
    DATASET_CSV = os.path.join(DATASET_DIR, 'gesture_landmarks.csv')
    CUSTOM_DATASET_CSV = os.path.join(DATASET_DIR, 'custom_landmarks.csv')
    
    MODEL_DIR = os.path.join(BASE_DIR, 'model')
    MODEL_PATH = os.path.join(MODEL_DIR, 'signai_classifier.pkl')
    ENCODER_PATH = os.path.join(MODEL_DIR, 'label_encoder.pkl')
    
    # Expanded Gesture Dictionary: Digits 0-9, ASL Alphabet A-Z, & Common Phrases
    GESTURES = {
        0:  {'name': 'Zero',     'code': '0', 'emoji': '✊', 'type': 'number'},
        1:  {'name': 'One',      'code': '1', 'emoji': '☝️', 'type': 'number'},
        2:  {'name': 'Two',      'code': '2', 'emoji': '✌️', 'type': 'number'},
        3:  {'name': 'Three',    'code': '3', 'emoji': '🤟', 'type': 'number'},
        4:  {'name': 'Four',     'code': '4', 'emoji': '🖐️', 'type': 'number'},
        5:  {'name': 'Five',     'code': '5', 'emoji': '✋', 'type': 'number'},
        6:  {'name': 'Six',      'code': '6', 'emoji': '🤙', 'type': 'number'},
        7:  {'name': 'Seven',    'code': '7', 'emoji': '🤚', 'type': 'number'},
        8:  {'name': 'Eight',    'code': '8', 'emoji': '👐', 'type': 'number'},
        9:  {'name': 'Nine',     'code': '9', 'emoji': '🤞', 'type': 'number'},
        10: {'name': 'Letter A', 'code': 'A', 'emoji': '🅰️', 'type': 'letter'},
        11: {'name': 'Letter B', 'code': 'B', 'emoji': '🅱️', 'type': 'letter'},
        12: {'name': 'Letter C', 'code': 'C', 'emoji': '🅲', 'type': 'letter'},
        13: {'name': 'Letter D', 'code': 'D', 'emoji': '🅳', 'type': 'letter'},
        14: {'name': 'Letter E', 'code': 'E', 'emoji': '🅴', 'type': 'letter'},
        15: {'name': 'Letter F', 'code': 'F', 'emoji': '🅵', 'type': 'letter'},
        16: {'name': 'Letter G', 'code': 'G', 'emoji': '🅛', 'type': 'letter'},
        17: {'name': 'Hello',    'code': 'H', 'emoji': '👋', 'type': 'word'},
        18: {'name': 'Thanks',   'code': 'T', 'emoji': '🙏', 'type': 'word'},
        19: {'name': 'Yes',      'code': 'Y', 'emoji': '👍', 'type': 'word'},
        20: {'name': 'No',       'code': 'N', 'emoji': '👎', 'type': 'word'},
        21: {'name': 'Love',     'code': 'L', 'emoji': '🤟', 'type': 'word'}
    }
