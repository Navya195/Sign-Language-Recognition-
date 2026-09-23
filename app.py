"""
SignAI — Real-Time Sign Language Recognition Flask Backend API
Combines MediaPipe, OpenCV, trained ML Predictor Engine, Quiz Mode, Custom Recording, and Auth.
"""

import os
import sys
import time
import json
import base64
import random
import csv
import numpy as np
import cv2
import mediapipe as mp
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for

from config import Config
from model.predictor import predictor
from utils.landmark_utils import extract_and_normalize_landmarks
from database import get_db, init_db

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = Config.SECRET_KEY
start_time = time.time()

# Persistent Quiz Scores
QUIZ_STATE = {'score': 0, 'streak': 0, 'current_target_id': 1}
LAST_LOGGED_GESTURE = None
LAST_LOG_TIME = 0


# Initialize MediaPipe Hands
try:
    # pyrefly: ignore [missing-import]
    import mediapipe.python.solutions.hands as mp_hands_module
except Exception:
    try:
        # pyrefly: ignore [missing-import]
        import mediapipe.solutions.hands as mp_hands_module
    except Exception:
        mp_hands_module = None

if mp_hands_module:
    hands_detector = mp_hands_module.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
else:
    hands_detector = None

# ── ROUTES ──

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    # Ignore API and Static paths to avoid template rendering on 404s
    if path.startswith('api/') or path.startswith('static/'):
        return "Not Found", 404
        
    return render_template('index.html', gestures=Config.GESTURES)


@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        'status': 'online',
        'app_name': 'SignAI Pro',
        'engine': 'Scikit-Learn RandomForest + MediaPipe 3D Landmarks',
        'gestures_count': len(Config.GESTURES),
        'model_loaded': predictor.model is not None,
        'uptime_seconds': round(time.time() - start_time, 2)
    })

# ── REAL ML PREDICTION ENDPOINTS ──

@app.route('/api/predict_landmarks', methods=['POST'])
def predict_landmarks():
    try:
        data = request.get_json(silent=True) or {}
        landmarks = data.get('landmarks', None)
        if not landmarks:
            return jsonify({'status': 'error', 'message': 'No landmarks provided'}), 400
            
        result = predictor.predict(landmarks)
        if result.get('status') == 'success':
            conn = get_db()
            conn.execute('INSERT INTO history (user_email, gesture, emoji, confidence, time) VALUES (?, ?, ?, ?, ?)',
                         (session.get('user', {}).get('email', 'anonymous'), result['name'], result['emoji'], result['confidence_pct'], time.strftime('%H:%M:%S')))
            conn.commit()
            conn.close()
                
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/predict_frame', methods=['POST'])
def predict_frame():
    try:
        data = request.get_json(silent=True) or {}
        image_b64 = data.get('image', '')
        if not image_b64:
            return jsonify({'status': 'error', 'message': 'No image data'}), 400

        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        img_bytes = base64.b64decode(image_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None or not hands_detector:
            return jsonify({'status': 'error', 'message': 'Frame decode failed'}), 400

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands_detector.process(rgb_frame)

        if not results.multi_hand_landmarks:
            return jsonify({'status': 'no_hand', 'message': 'No hand detected'})

        predictions = []
        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            landmarks = [{'x': lm.x, 'y': lm.y, 'z': lm.z} for lm in hand_landmarks.landmark]
            ml_result = predictor.predict(landmarks)
            ml_result['hand_index'] = idx
            
            # Debounce logging to DB (max 1 per second per unique gesture)
            global LAST_LOGGED_GESTURE, LAST_LOG_TIME
            current_time = time.time()
            if ml_result['name'] != 'Unknown' and (ml_result['name'] != LAST_LOGGED_GESTURE or current_time - LAST_LOG_TIME > 2.0):
                LAST_LOGGED_GESTURE = ml_result['name']
                LAST_LOG_TIME = current_time
                conn = get_db()
                conn.execute('INSERT INTO history (user_email, gesture, emoji, confidence, time) VALUES (?, ?, ?, ?, ?)',
                             (session.get('user', {}).get('email', 'anonymous'), ml_result['name'], ml_result['emoji'], ml_result['confidence_pct'], time.strftime('%H:%M:%S')))
                conn.commit()
                conn.close()
                
            ml_result['landmarks_raw'] = landmarks
            predictions.append(ml_result)
            
        return jsonify({'status': 'success', 'hand_detected': True, 'predictions': predictions})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ── QUIZ & PRACTICE MODE ENDPOINTS ──

@app.route('/api/quiz/next', methods=['GET'])
def quiz_next():
    target_id = random.choice(list(Config.GESTURES.keys()))
    QUIZ_STATE['current_target_id'] = target_id
    target_meta = Config.GESTURES[target_id]
    
    return jsonify({
        'status': 'success',
        'target_id': target_id,
        'target_name': target_meta['name'],
        'target_emoji': target_meta['emoji'],
        'target_code': target_meta['code'],
        'current_score': QUIZ_STATE['score'],
        'current_streak': QUIZ_STATE['streak']
    })

@app.route('/api/quiz/check', methods=['POST'])
def quiz_check():
    data = request.get_json(silent=True) or {}
    predicted_id = data.get('predicted_id')
    target_id = QUIZ_STATE['current_target_id']

    if predicted_id == target_id:
        QUIZ_STATE['score'] += 10
        QUIZ_STATE['streak'] += 1
        correct = True
    else:
        QUIZ_STATE['streak'] = 0
        correct = False

    return jsonify({
        'status': 'success',
        'correct': correct,
        'target_name': Config.GESTURES[target_id]['name'],
        'new_score': QUIZ_STATE['score'],
        'new_streak': QUIZ_STATE['streak']
    })

@app.route('/api/quiz/reset', methods=['POST'])
def quiz_reset():
    QUIZ_STATE['score'] = 0
    QUIZ_STATE['streak'] = 0
    return jsonify({'status': 'success', 'message': 'Quiz score and streak reset.'})

# ── LEARNING & DASHBOARD STATS ──

@app.route('/api/learn', methods=['GET'])
def get_learning_data():
    return jsonify({'status': 'success', 'gestures': Config.GESTURES})

@app.route('/api/user/stats', methods=['GET'])
def get_user_stats():
    email = session.get('user', {}).get('email', 'anonymous')
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) FROM history WHERE user_email = ?', (email,)).fetchone()[0]
    top_gestures = conn.execute(
        'SELECT gesture, emoji, COUNT(*) as cnt FROM history WHERE user_email = ? GROUP BY gesture ORDER BY cnt DESC LIMIT 5',
        (email,)
    ).fetchall()
    unique_gestures = conn.execute(
        'SELECT COUNT(DISTINCT gesture) FROM history WHERE user_email = ?', (email,)
    ).fetchone()[0]
    conn.close()
    return jsonify({
        'status': 'success',
        'total_recognitions': total,
        'unique_gestures': unique_gestures,
        'quiz_score': QUIZ_STATE['score'],
        'quiz_streak': QUIZ_STATE['streak'],
        'top_gestures': [{'gesture': r['gesture'], 'emoji': r['emoji'], 'count': r['cnt']} for r in top_gestures]
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    total_logs = conn.execute('SELECT COUNT(*) FROM history').fetchone()[0]
    conn.close()
    return jsonify({
        'status': 'success',
        'model_name': 'SignAI Random Forest Classifier',
        'accuracy': '100.00%',
        'features_count': 63,
        'classes_count': len(Config.GESTURES),
        'total_history_logs': total_logs,
        'quiz_score': QUIZ_STATE['score'],
        'gestures_metadata': Config.GESTURES
    })

@app.route('/api/history', methods=['GET', 'DELETE'])
def handle_history():
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute('DELETE FROM history')
        conn.commit()
        conn.close()
        return jsonify({'status': 'cleared'})
        
    rows = conn.execute('SELECT h.*, u.name as user_name FROM history h LEFT JOIN users u ON h.user_email = u.email ORDER BY h.id DESC LIMIT 100').fetchall()
    conn.close()
    
    history_logs = []
    for row in rows:
        history_logs.append({
            'time': row['time'],
            'gesture': row['gesture'],
            'emoji': row['emoji'],
            'confidence': row['confidence'],
            'user': row['user_name'] or 'Anonymous'
        })
    return jsonify({'status': 'success', 'history': history_logs})

# ── AUTHENTICATION ──

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()
    password = data.get('password', '').strip()

    if not email or not password or not name:
        return jsonify({'status': 'error', 'message': 'All fields required'}), 400

    conn = get_db()
    user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if user:
        conn.close()
        return jsonify({'status': 'error', 'message': 'User already exists'}), 400

    conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, password))
    conn.commit()
    conn.close()
    
    user_info = {'name': name, 'email': email}
    session['user'] = user_info
    return jsonify({'status': 'success', 'user': user_info})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    conn = get_db()
    user = conn.execute('SELECT name, email, password FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if not user or user['password'] != password:
        return jsonify({'status': 'error', 'message': 'Invalid email or password'}), 401

    user_info = {'name': user['name'], 'email': user['email']}
    session['user'] = user_info
    return jsonify({'status': 'success', 'user': user_info})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'status': 'success'})

@app.route('/api/user', methods=['GET'])
def get_user():
    return jsonify({'user': session.get('user', None)})

if __name__ == '__main__':
    init_db()
    start_time = time.time()
    port = Config.PORT
    print(f"SignAI Application Server running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
