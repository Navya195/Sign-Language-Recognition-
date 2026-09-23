/**
 * SignAI — Real-Time Landmark Tracking, Quiz Mode & Speech Synthesis Engine
 */

let isRunning = false;
let videoStream = null;
let animFrameId = null;
let lastPredictionTime = 0;
let sentenceWords = [];
let currentUser = null;
let historyRecords = [];
let currentQuizTarget = null;
let isQuizActive = false;

let video = null;
let canvas = null;
let ctx = null;
let lastFrameTime = 0;
let fpsValue = 0;
let lastHandCount = 0;
let lastPredictions = [];

// ── GLOBAL APP SETTINGS (updated live from Settings page) ──
const appSettings = {
  confThreshold: 50,
  predInterval: 300,
  debounce: 2.0,
  showHUD: true,
  showSkeleton: true,
  showLabel: true,
  autoAppend: true,
  ttsRate: 1.0,
  ttsVoice: ''
};

function initCanvas() {
  if (!video) video = document.getElementById('videoFeed');
  if (!canvas) canvas = document.getElementById('videoCanvas');
  if (canvas && !ctx) ctx = canvas.getContext('2d');
}

// ── NAVIGATION & ROUTING ──
window.addEventListener('popstate', () => {
  handleRoute(window.location.pathname, false);
});

function handleRoute(path, push = true) {
  if (push) {
    window.history.pushState(null, '', path);
  }

  let viewName = path.replace(/^\//, '');
  if (!viewName || viewName === 'login') {
    showLoginView();
    return;
  }
  
  if (viewName === 'home') {
    showHomeView();
    return;
  }

  showDashboardView();
  switchView(viewName);
}

function switchView(viewName) {
  document.querySelectorAll('.page-view').forEach(el => el.classList.remove('active-view'));
  document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

  const view = document.getElementById('view-' + viewName);
  const nav = document.getElementById('nav-' + viewName);

  if (view) view.classList.add('active-view');
  if (nav) nav.classList.add('active');

  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Load specific data based on view
  if (viewName === 'dashboard') {
    fetchUserStats();
  } else if (viewName === 'history') {
    fetchHistory();
  } else if (viewName === 'ml-dashboard') {
    fetchStats();
  } else if (viewName === 'quiz') {
    startQuiz();
  }
}

// ── WEBCAM & TRACKING LOOP ──
async function startCamera() {
  initCanvas();
  try {
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' },
      audio: false
    });

    video.srcObject = videoStream;
    video.style.display = 'block';
    document.getElementById('camIdle').style.display = 'none';
    document.getElementById('scanline').style.display = 'block';

    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;

    isRunning = true;
    showToast('Webcam stream started. AI Gesture recognition active.');

    video.onloadedmetadata = () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      processLoop();
    };
  } catch (err) {
    alert('Failed to access webcam: ' + err.message);
  }
}

function stopCamera() {
  isRunning = false;
  if (animFrameId) cancelAnimationFrame(animFrameId);
  if (videoStream) videoStream.getTracks().forEach(track => track.stop());

  video.style.display = 'none';
  document.getElementById('camIdle').style.display = 'flex';
  document.getElementById('scanline').style.display = 'none';

  document.getElementById('startBtn').disabled = false;
  document.getElementById('stopBtn').disabled = true;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  showToast('Webcam feed stopped.');
}

function processLoop() {
  if (!isRunning) return;
  animFrameId = requestAnimationFrame(processLoop);

  if (video.readyState < 2) return;

  // Calculate FPS
  const frameNow = performance.now();
  if (lastFrameTime > 0) {
    fpsValue = Math.round(1000 / (frameNow - lastFrameTime));
  }
  lastFrameTime = frameNow;

  // Render mirrored frame to canvas
  ctx.save();
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  ctx.restore();

  // Draw HUD overlay on canvas
  drawHUD();

  const now = Date.now();
  if (now - lastPredictionTime > appSettings.predInterval) {
    lastPredictionTime = now;
    const frameData = canvas.toDataURL('image/jpeg', 0.6);
    
    fetch('/api/predict_frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: frameData })
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success' && data.predictions) {
        lastHandCount = data.predictions.length;
        lastPredictions = data.predictions;
        updatePredictionUI(data.predictions);

        // If in Quiz mode, evaluate answer against target! (Use primary hand)
        if (isQuizActive && currentQuizTarget && data.predictions.length > 0) {
          checkQuizAnswer(data.predictions[0].gesture_id);
        }
      } else if (data.status === 'no_hand') {
        lastHandCount = 0;
        lastPredictions = [];
      }
    })
    .catch(() => {});
  }
}

const HAND_CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],         // Thumb
  [0,5],[5,6],[6,7],[7,8],         // Index
  [0,9],[9,10],[10,11],[11,12],    // Middle
  [0,13],[13,14],[14,15],[15,16],  // Ring
  [0,17],[17,18],[18,19],[19,20],  // Pinky
  [5,9],[9,13],[13,17]             // Palm
];

function drawHUD() {
  const W = canvas.width;
  const H = canvas.height;

  // FPS Badge (only if HUD enabled)
  if (appSettings.showHUD) {
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.55)';
    ctx.beginPath();
    ctx.roundRect(10, 10, 90, 28, 5);
    ctx.fill();
    ctx.fillStyle = fpsValue >= 20 ? '#10b981' : '#ef4444';
    ctx.font = 'bold 12px monospace';
    ctx.fillText(`FPS: ${fpsValue}`, 20, 28);
    ctx.restore();

    // Hands Badge
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.55)';
    ctx.beginPath();
    ctx.roundRect(W - 120, 10, 110, 28, 5);
    ctx.fill();
    ctx.fillStyle = lastHandCount > 0 ? '#6366f1' : '#64748b';
    ctx.font = 'bold 12px monospace';
    ctx.fillText(`HANDS: ${lastHandCount}`, W - 110, 28);
    ctx.restore();
  }

  // Draw skeleton for each detected hand (only if enabled)
  lastPredictions.forEach((pred, handIdx) => {
    if (!pred.landmarks_raw) return;
    const color = handIdx === 0 ? '#6366f1' : '#8b5cf6';
    const lms = pred.landmarks_raw;

    if (appSettings.showSkeleton) {
      // Draw connections
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.globalAlpha = 0.8;
      HAND_CONNECTIONS.forEach(([a, b]) => {
        if (!lms[a] || !lms[b]) return;
        ctx.beginPath();
        ctx.moveTo((1 - lms[a].x) * W, lms[a].y * H);
        ctx.lineTo((1 - lms[b].x) * W, lms[b].y * H);
        ctx.stroke();
      });

      // Draw joints
      lms.forEach(lm => {
        ctx.beginPath();
        ctx.arc((1 - lm.x) * W, lm.y * H, 4, 0, 2 * Math.PI);
        ctx.fillStyle = '#fff';
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();
      });
      ctx.restore();
    }

    // Label above wrist
    if (appSettings.showLabel && lms[0]) {
      ctx.save();
      const label = pred.code || pred.name;
      ctx.font = 'bold 14px Inter, sans-serif';
      const tw = ctx.measureText(label).width;
      const lx = (1 - lms[0].x) * W - tw / 2;
      const ly = lms[0].y * H - 14;
      ctx.fillStyle = 'rgba(0,0,0,0.6)';
      ctx.beginPath();
      ctx.roundRect(lx - 6, ly - 14, tw + 12, 20, 4);
      ctx.fill();
      ctx.fillStyle = color;
      ctx.fillText(label, lx, ly);
      ctx.restore();
    }
  });
}

// ── UI PREDICTION UPDATES ──
function updatePredictionUI(predictions) {
  // Clear chips
  document.querySelectorAll('.gesture-chip').forEach(el => el.classList.remove('active'));

  // Reset UI for both hands
  for (let i = 0; i < 2; i++) {
    const sym = document.getElementById('predSymbol_' + i);
    if (sym) {
      sym.textContent = '—';
      document.getElementById('predWord_' + i).textContent = 'Waiting...';
      document.getElementById('confPct_' + i).textContent = '0%';
      document.getElementById('confFill_' + i).style.width = '0%';
    }
  }

  // Update with active hands
  predictions.forEach((pred, index) => {
    if (index > 1) return; // Support max 2 hands in UI
    
    // Apply confidence threshold filter
    if (pred.confidence_pct < appSettings.confThreshold) {
      document.getElementById('predWord_' + index).textContent = 'Below threshold';
      document.getElementById('confPct_' + index).textContent = `${pred.confidence_pct}%`;
      document.getElementById('confFill_' + index).style.width = `${pred.confidence_pct}%`;
      return;
    }
    
    document.getElementById('predSymbol_' + index).textContent = pred.code || '—';
    document.getElementById('predWord_' + index).textContent = `${pred.emoji} ${pred.name}`;
    document.getElementById('confPct_' + index).textContent = `${pred.confidence_pct}%`;
    document.getElementById('confFill_' + index).style.width = `${pred.confidence_pct}%`;

    const chip = document.getElementById('chip-' + pred.gesture_id);
    if (chip) chip.classList.add('active');

    if (document.getElementById('ttsToggle') && document.getElementById('ttsToggle').checked) {
      speakWord(pred.name);
    }
    if (appSettings.autoAppend) appendWord(pred.name);
  });
}

// ── INTERACTIVE QUIZ & PRACTICE MODE ──
function startQuiz() {
  isQuizActive = true;
  fetchNextQuizQuestion();
}

function fetchNextQuizQuestion() {
  fetch('/api/quiz/next')
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        currentQuizTarget = data;
        document.getElementById('quizTargetEmoji').textContent = data.target_emoji;
        document.getElementById('quizTargetName').textContent = data.target_name;
        document.getElementById('quizTargetCode').textContent = data.target_code;
        document.getElementById('quizScore').textContent = data.current_score;
        document.getElementById('quizStreak').textContent = data.current_streak;
        document.getElementById('quizResultBanner').style.display = 'none';
      }
    });
}

function checkQuizAnswer(predictedId) {
  if (!currentQuizTarget) return;

  fetch('/api/quiz/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ predicted_id: predictedId })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'success') {
      const banner = document.getElementById('quizResultBanner');
      banner.style.display = 'block';
      
      if (data.correct) {
        banner.className = 'card';
        banner.style.borderColor = 'var(--accent)';
        banner.innerHTML = `<span style="color:var(--accent); font-weight:700;">🎉 Correct! +10 Points!</span>`;
        speakWord('Correct!');
        setTimeout(fetchNextQuizQuestion, 2000);
      } else {
        banner.className = 'card';
        banner.style.borderColor = 'var(--accent-red)';
        banner.innerHTML = `<span style="color:var(--accent-red); font-weight:700;">❌ Keep Trying! Show sign for "${currentQuizTarget.target_name}"</span>`;
      }

      document.getElementById('quizScore').textContent = data.new_score;
      document.getElementById('quizStreak').textContent = data.new_streak;
    }
  });
}

// ── SENTENCE BUILDER & SPEECH (TTS) ──
function speakWord(text) {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = appSettings.ttsRate;
    
    if (appSettings.ttsVoice) {
      const voices = window.speechSynthesis.getVoices();
      const selected = voices.find(v => v.name === appSettings.ttsVoice);
      if (selected) utterance.voice = selected;
    }
    
    window.speechSynthesis.speak(utterance);
  }
}

function appendWord(word) {
  if (sentenceWords[sentenceWords.length - 1] !== word) {
    sentenceWords.push(word);
    renderSentence();
  }
}

function renderSentence() {
  const container = document.getElementById('sentenceText');
  if (!container) return;
  
  if (sentenceWords.length === 0) {
    container.innerHTML = `<span style="color:var(--text-dim); font-style:italic;">Translated signs will appear here...</span>`;
  } else {
    container.textContent = sentenceWords.join(' ');
  }
}

function addSpace() {
  sentenceWords.push(' ');
  renderSentence();
}

function speakFullSentence() {
  const text = sentenceWords.join(' ');
  if (text.trim()) {
    speakWord(text);
    showToast('Speaking sentence...');
  }
}

function copySentenceText() {
  const text = sentenceWords.join(' ');
  if (text.trim()) {
    navigator.clipboard.writeText(text);
    showToast('Copied to clipboard!');
  }
}

function clearSentenceText() {
  sentenceWords = [];
  renderSentence();
  showToast('Sentence cleared.');
}

function clearHistory() {
  if (confirm('Delete all recognition history? This cannot be undone.')) {
    fetch('/api/history', { method: 'DELETE' })
      .then(res => res.json())
      .then(() => {
        historyRecords = [];
        renderHistoryTable([]);
        showToast('All recognition history cleared.');
      });
  }
}

// ── USER PROFILE STATS ──
function fetchUserStats() {
  fetch('/api/user/stats')
    .then(res => res.json())
    .then(data => {
      if (data.status !== 'success') return;

      document.getElementById('profileTotalRec').textContent = data.total_recognitions;
      document.getElementById('profileUniqueGest').textContent = data.unique_gestures;
      document.getElementById('profileQuizScore').textContent = data.quiz_score;
      document.getElementById('profileStreak').textContent = data.quiz_streak;

      // Update account name/email from currentUser
      if (currentUser) {
        document.getElementById('profileName').textContent = currentUser.name;
        document.getElementById('profileEmail').textContent = currentUser.email;
        document.getElementById('profileAuthBtn').textContent = 'Sign Out';
        document.getElementById('profileAuthBtn').onclick = logoutUser;
      }

      // Render top gestures bar chart
      const container = document.getElementById('profileTopGestures');
      if (!container) return;

      if (!data.top_gestures || data.top_gestures.length === 0) {
        container.innerHTML = '<div style="color:var(--text-dim); font-size:0.85rem;">Make some predictions to see your top gestures...</div>';
        return;
      }

      const maxCount = data.top_gestures[0].count;
      const colors = ['var(--primary)', 'var(--accent-purple)', 'var(--accent-green)', 'var(--accent-yellow)', 'var(--accent-pink)'];

      container.innerHTML = data.top_gestures.map((g, i) => `
        <div>
          <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:4px;">
            <span style="font-weight:600;">${g.emoji} ${g.gesture}</span>
            <span style="color:var(--text-dim); font-family:var(--font-mono);">${g.count}x</span>
          </div>
          <div style="height:8px; background:var(--bg-main); border-radius:var(--radius-full); overflow:hidden;">
            <div style="height:100%; width:${Math.round((g.count/maxCount)*100)}%; background:${colors[i]}; border-radius:var(--radius-full); transition:width 0.6s ease;"></div>
          </div>
        </div>
      `).join('');
    });
}

// ── DASHBOARD & HISTORY LOGS ──
function fetchHistory() {
  fetch('/api/history')
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        historyRecords = data.history;
        renderHistoryTable(data.history);
      }
    });
}

function renderHistoryTable(logs) {
  const container = document.getElementById('historyTableBody');
  if (!container) return;

  if (!logs || logs.length === 0) {
    container.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-dim); padding:20px;">No gesture records found yet.</td></tr>`;
    return;
  }

  container.innerHTML = logs.map(row => `
    <tr style="border-bottom:1px solid var(--border);">
      <td style="padding:10px; font-family:var(--font-mono); font-size:0.8rem; color:var(--text-dim);">${row.time}</td>
      <td style="padding:10px; font-weight:600; color:var(--accent);">${row.emoji} ${row.gesture}</td>
      <td style="padding:10px; font-family:var(--font-mono); color:var(--accent-purple);">${row.confidence}%</td>
      <td style="padding:10px; color:var(--text-muted);">${row.user || 'Anonymous'}</td>
      <td style="padding:10px;"><button class="btn btn-outline btn-sm" onclick="speakWord('${row.gesture}')">🔊 Speak</button></td>
    </tr>
  `).join('');
}

function exportHistoryCSV() {
  if (!historyRecords || historyRecords.length === 0) {
    showToast('No history records to export.');
    return;
  }

  let csvContent = "data:text/csv;charset=utf-8,Time,Gesture,Confidence,User\n";
  historyRecords.forEach(r => {
    csvContent += `"${r.time}","${r.gesture}","${r.confidence}%","${r.user}"\n`;
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `SignAI_History_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('Exported history to CSV file.');
}

function fetchStats() {
  fetch('/api/stats')
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        if (document.getElementById('statAccuracy')) document.getElementById('statAccuracy').textContent = data.accuracy;
        if (document.getElementById('statModelName')) document.getElementById('statModelName').textContent = data.model_name;
        if (document.getElementById('statClassesCount')) document.getElementById('statClassesCount').textContent = data.classes_count;
      }
    });
}

// ── AUTHENTICATION ──
function showLoginView() {
  document.getElementById('loginView').style.display = 'flex';
  document.getElementById('homeView').style.display = 'none';
  document.getElementById('mainDashboard').style.display = 'none';
}

function showHomeView() {
  document.getElementById('loginView').style.display = 'none';
  document.getElementById('homeView').style.display = 'flex';
  document.getElementById('mainDashboard').style.display = 'none';
}

function showDashboardView() {
  document.getElementById('loginView').style.display = 'none';
  document.getElementById('homeView').style.display = 'none';
  document.getElementById('mainDashboard').style.display = 'grid'; // .dashboard-layout uses grid
  // In case of mobile where it collapses, CSS media queries will handle the layout since the class is active.
}

function switchAuthTab(tab) {
  document.querySelectorAll('.auth-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');

  if (tab === 'login') {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('signupForm').style.display = 'none';
  } else {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('signupForm').style.display = 'block';
  }
}

function handleAuthSubmit(event, mode) {
  event.preventDefault();
  const endpoint = mode === 'login' ? '/api/login' : '/api/register';
  
  const payload = mode === 'login' ? {
    email: document.getElementById('loginEmail').value,
    password: document.getElementById('loginPass').value
  } : {
    name: document.getElementById('signupName').value,
    email: document.getElementById('signupEmail').value,
    password: document.getElementById('signupPass').value
  };

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'success') {
      currentUser = data.user;
      document.getElementById('userStatusText').textContent = `Logged in: ${currentUser.name}`;
      document.getElementById('authNavBtn').textContent = `Sign Out`;
      handleRoute('/home');
      showToast(`Welcome, ${currentUser.name}!`);
    } else {
      alert(data.message || 'Authentication failed');
    }
  });
}

function logoutUser() {
  if (confirm('Sign out of your account?')) {
    fetch('/api/logout', { method: 'POST' }).then(() => {
      currentUser = null;
      document.getElementById('userStatusText').textContent = 'System Ready';
      handleRoute('/login');
      showToast('Signed out.');
    });
  }
}

function showToast(msg) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>✨</span><span>${msg}</span>`;
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(30px)';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ── SETTINGS ENGINE ──
function updateSetting(key, value) {
  if (key === 'confThreshold') {
    appSettings.confThreshold = parseInt(value);
    document.getElementById('confThreshLabel').textContent = value + '%';
    showToast(`Confidence threshold set to ${value}%`);
  } else if (key === 'predInterval') {
    appSettings.predInterval = parseInt(value);
    document.getElementById('predSpeedLabel').textContent = value + 'ms';
  } else if (key === 'debounce') {
    appSettings.debounce = parseFloat(value);
    document.getElementById('debounceLabel').textContent = parseFloat(value).toFixed(1) + 's';
  } else if (key === 'showHUD') {
    appSettings.showHUD = value;
    showToast(`HUD ${value ? 'enabled' : 'disabled'}`);
  } else if (key === 'showSkeleton') {
    appSettings.showSkeleton = value;
    showToast(`Skeleton overlay ${value ? 'enabled' : 'disabled'}`);
  } else if (key === 'showLabel') {
    appSettings.showLabel = value;
  } else if (key === 'autoAppend') {
    appSettings.autoAppend = value;
    showToast(`Auto-append ${value ? 'enabled' : 'disabled'}`);
  } else if (key === 'ttsRate') {
    appSettings.ttsRate = parseFloat(value);
    document.getElementById('ttsRateLabel').textContent = parseFloat(value).toFixed(1) + 'x';
  } else if (key === 'ttsVoice') {
    appSettings.ttsVoice = value;
  }
}

function testTTS() {
  speakWord('Hello! SignAI text to speech is working correctly.');
  showToast('Testing TTS voice...');
}

function resetQuizScore() {
  if (confirm('Reset quiz score and streak to zero?')) {
    fetch('/api/quiz/reset', { method: 'POST' })
      .catch(() => {})
      .finally(() => {
        document.getElementById('quizScore') && (document.getElementById('quizScore').textContent = '0');
        document.getElementById('quizStreak') && (document.getElementById('quizStreak').textContent = '0');
        showToast('Quiz score and streak reset.');
      });
  }
}

function populateTTSVoices() {
  if (!('speechSynthesis' in window)) return;
  const select = document.getElementById('ttsVoiceSelect');
  if (!select) return;
  const voices = window.speechSynthesis.getVoices();
  voices.forEach(v => {
    const opt = document.createElement('option');
    opt.value = v.name;
    opt.textContent = `${v.name} (${v.lang})`;
    select.appendChild(opt);
  });
}

if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = populateTTSVoices;
  window.addEventListener('load', () => setTimeout(populateTTSVoices, 500));
}

// ── SPLASH SCREEN LOADER & INITIALIZATION ──
window.addEventListener('load', () => {
  // Check if user is already authenticated
  fetch('/api/user')
    .then(res => res.json())
    .then(data => {
      if (data.user) {
        currentUser = data.user;
        document.getElementById('userStatusText').textContent = `Logged in: ${currentUser.name}`;
        document.getElementById('authNavBtn').textContent = `Sign Out`;
        
        let initialPath = window.location.pathname;
        if (initialPath === '/' || initialPath === '/login') initialPath = '/home';
        handleRoute(initialPath, false);
      } else {
        handleRoute('/login', false);
      }

      // Hide Splash Screen once initialized
      const splash = document.getElementById('splashScreen');
      if (splash) {
        setTimeout(() => {
          splash.classList.add('hidden');
          setTimeout(() => splash.style.display = 'none', 600);
        }, 800);
      }
    })
    .catch(() => {
      handleRoute('/login', false);
      const splash = document.getElementById('splashScreen');
      if (splash) {
        splash.classList.add('hidden');
        setTimeout(() => splash.style.display = 'none', 600);
      }
    });
});
