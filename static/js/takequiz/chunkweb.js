const Logger = (function () {
    'use strict';

    const LOG_KEY = 'quizViolationsLog';
    const SESSION_KEY = 'quizSessionId';
    const CHUNK_KEY = 'currentChunkIndex';
    let logs = [];
    let autoFlushIntervalId = null; // <-- переменная для таймера

    const sessionId = (function () {
        let id = localStorage.getItem(SESSION_KEY);
        if (!id) {
            id = '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem(SESSION_KEY, id);
        }
        return id;
    })();

    function load() {
        try {
            const raw = localStorage.getItem(LOG_KEY);
            logs = raw ? JSON.parse(raw) : [];
        } catch {
            logs = [];
        }
    }

    function save() {
        localStorage.setItem(LOG_KEY, JSON.stringify(logs));
    }

    function log(event, detail = '') {
        const entry = {
            event,
            detail,
            timestamp: new Date().toISOString(),
            session_id: sessionId,
            chunk_index: getCurrentChunkIndex(),
        };
        logs.push(entry);
        save();
        console.debug('📝 Log:', entry);
    }

    function setCurrentChunkIndex(index) {
        localStorage.setItem(CHUNK_KEY, index.toString());
    }

    function getCurrentChunkIndex() {
        const val = localStorage.getItem(CHUNK_KEY);
        return val ? parseInt(val, 10) : null;
    }

    async function flush() {
        if (logs.length === 0) return;

        try {
            const response = await fetch('/api/upload-logs/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({logs}),
            });

            if (response.ok) {
                console.log('✅ Логи успешно отправлены на сервер');
                logs = [];
                save();
            } else {
                console.warn('⚠️ Не удалось отправить логи', response.status);
            }
        } catch (error) {
            console.error('❌ Ошибка отправки логов:', error);
        }
    }

    function getLogs() {
        return logs;
    }

    function autoFlush(intervalMs = 30000) {  // <-- по умолчанию 30 секунд
        if (autoFlushIntervalId !== null) {
            clearInterval(autoFlushIntervalId); // чтобы не запускать дважды
        }
        autoFlushIntervalId = setInterval(() => {
            flush();
        }, intervalMs);
        console.log(`🛠️ Авто-флаш логов каждые ${intervalMs / 1000} секунд активирован`);
    }

    // Инициализация
    load();

    return {
        log,
        flush,
        setCurrentChunkIndex,
        getCurrentChunkIndex,
        getLogs,
        sessionId,
        autoFlush,   // <-- экспортируем новую функцию
    };
})();


Logger.log('page_opened');


let room;
let chunkIndex = 0;
let isRecording = false;
let chunkTimer;

async function startProctoringStream() {
    const livekitUrl = "wss://livekit.odx.kz";
    const tokenRes = await fetch('/api/livekit/token?room=default-room');
    const {token} = await tokenRes.json();

    room = new LivekitClient.Room({
        adaptiveStream: true,
        dynacast: true,
    });

    await room.connect(livekitUrl, token);
    console.log('🟢 Подключились к LiveKit');

    const iframe = document.getElementById('proctorFrame');
    const iframeDoc = iframe.contentWindow.document;
    const video = iframeDoc.getElementById('video');
    const log = iframeDoc.getElementById('log');
    const checklist = iframeDoc.getElementById('checklist');
    const violationToast = iframeDoc.getElementById('violationToastbody');

    if (!video) {
        console.warn("⚠️ Видео в iframe не найдено");
        return;
    }

    const audioStream = await navigator.mediaDevices.getUserMedia({audio: true});
    const canvas = document.createElement('canvas');
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d', {willReadFrequently: true});
    const exId = document.getElementById('externalId');

    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const violation = violationToast?.textContent?.trim();
        const externalId = exId.textContent || 'N/A';
        const checklistText = checklist?.textContent || '';

        // === Верхний правый угол: Время и ID ===
        const timeStr = new Date().toLocaleTimeString();
        const text = `${timeStr} | ID: ${externalId}`;

        ctx.save();
        ctx.font = "12px monospace";
        const padding = 6;
        const textWidth = ctx.measureText(text).width;
        const bgHeight = 20;

        const x = canvas.width - textWidth - padding * 2;
        const y = 5;

        ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
        ctx.fillRect(x, y, textWidth + padding * 2, bgHeight);

        ctx.fillStyle = "white";
        ctx.fillText(text, x + padding, y + 14 - 6); // по центру
        ctx.restore();

        // === Нижняя панель: чеклист ===

        ctx.font = "11px monospace";
        ctx.textBaseline = "top";

        const lineHeight = 14;
        let cx = padding;
        let cy = canvas.height - 20;

        const checklistItems = checklistText.replace(/<br\s*\/?>/gi, '\n').split('\n').filter(Boolean);

        checklistItems.forEach((item) => {
            ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
            const cleanItem = item.trim();
            if (!cleanItem) return;
            ctx.fillStyle = cleanItem.includes('❌') ? "rgba(255, 0, 0, 0.5)" :
                cleanItem.includes('✅') ? "rgba(0, 128, 0, 0.0)" : "rgba(255, 255, 255, 0.0)";

            if (cleanItem.includes('❌ Лицо не найдено')) {
                ctx.save();
                ctx.fillStyle = "rgba(255, 0, 0, 0.8)";
                ctx.font = "bold 16px sans-serif";
                ctx.textAlign = "center";
                ctx.fillText("⚠️ Внимание: Лицо не найдено!", canvas.width / 2, canvas.height / 2);
                ctx.restore();
            }
            if (cleanItem.includes('❌ Несколько лиц в кадре')) {
                ctx.save();
                ctx.fillStyle = "rgba(255, 0, 0, 0.8)";
                ctx.font = "bold 16px sans-serif";
                ctx.textAlign = "center";
                ctx.fillText("⚠️ Внимание: Несколько лиц в кадре!", canvas.width / 2, canvas.height / 2);
                ctx.restore();
            }
            ctx.fillRect(0, canvas.height - 30, canvas.width, 30);
            ctx.fillStyle = "white";
            const words = cleanItem.split(' ');

            for (const word of words) {
                const measure = ctx.measureText(word + ' ');
                if (cx + measure.width > canvas.width - padding) {
                    cx = padding;
                    cy += lineHeight;
                }
                ctx.fillText(word + ' ', cx, cy);
                cx += measure.width;
            }
        });

        // === Рамка ===
        ctx.lineWidth = violation ? 5 : 2;
        ctx.strokeStyle = violation ? "red" : "lime";
        ctx.strokeRect(0, 0, canvas.width, canvas.height);
        if (document.hidden) {
            ctx.save();
            ctx.fillStyle = "rgba(255, 0, 0, 0.8)";
            ctx.font = "bold 16px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("⚠️ Внимание: вкладка неактивна!", canvas.width / 2, canvas.height / 2);
            ctx.restore();
        }
        setTimeout(draw, 100); // или даже 200

    }

    draw();
    const canvasStream = canvas.captureStream(10); // 10 FPS
    const combinedStream = new MediaStream([
        ...canvasStream.getVideoTracks(),
        ...audioStream.getAudioTracks()
    ]);

    // 🟢 Публикуем в комнату LiveKit
    const publication = await room.localParticipant.publishTrack(canvasStream.getVideoTracks()[0], {
        name: 'canvas-stream',
        source: LivekitClient.Track.Source.Camera,
    });
    console.log('🚀 Канвас-трек опубликован:', publication.trackSid);

    // 🟢 Параллельно пишем чанки
    startChunkRecording(combinedStream);
}

// function startChunkRecording(stream) {
//     const recorder = new MediaRecorder(stream, {mimeType: 'video/webm'});
//
//     recorder.ondataavailable = async (e) => {
//         console.log('📦 Data available:', e.data.size);
//         if (e.data.size > 0) {
//             await uploadChunk(e.data);
//         }
//     };
//
//     recorder.start(20000); // каждый чанк 20 сек
//     console.log('🔴 Запись чанков началась');
//     isRecording = true;
// }
function startChunkRecording(stream) {
    async function recordChunk(index) {
        const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
        let chunks = [];

        recorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                chunks.push(e.data);
            }
        };

        recorder.onstop = async () => {
            const blob = new Blob(chunks, { type: 'video/webm' });
            await uploadChunk(blob);
            Logger.setCurrentChunkIndex(index);
            Logger.log('chunk_uploaded', `Залит чанк #${index}`);

            // Запускаем следующий чанк
            recordChunk(index + 1);
        };

        recorder.start();
        console.log(`📹 Чанк #${index} — запись началась`);

        setTimeout(() => {
            if (recorder.state === 'recording') {
                recorder.stop();
            }
        }, 20000);
    }

    recordChunk(chunkIndex);
}



async function uploadChunk(blob) {
    try {
        await Logger.flush();

        const res = await fetch(`/api/get-presigned-url/?index=${chunkIndex}&content_type=video/webm`);
        const {url, key} = await res.json();

        const upload = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'video/webm'
            },
            body: blob
        });

        if (!upload.ok) throw new Error(`HTTP ${upload.status}`);

        Logger.setCurrentChunkIndex(chunkIndex);  // ОБНОВЛЯЕМ для логгера
        Logger.log('chunk_uploaded', `☁️ Чанк #${chunkIndex} залит в ${key}`);

        chunkIndex++;
    } catch (err) {
        Logger.log('chunk_upload_error', err.message);
        console.error("❌ Ошибка заливки чанка:", err);
    }
}


// 🛑 Останавливаем запись при выходе
window.addEventListener('beforeunload', async () => {
    if (room) {
        room.disconnect();
    }
    if (isRecording) {
        clearInterval(chunkTimer);
    }
    await Logger.flush(); // <-- ДОБАВИТЬ
});


// 🚀 Стартуем когда iframe готов
document.getElementById('proctorFrame').addEventListener('load', () => {
    startProctoringStream();
});


const toastEl = document.getElementById('violationToast');
const toast = bootstrap.Toast.getOrCreateInstance(toastEl);

function showViolation(message) {
    toastEl.querySelector('.toast-body').textContent = message;
    toast.show();
    Logger.log('violation', message);
}

document.addEventListener('contextmenu', e => {
    e.preventDefault();
    showViolation('Правый клик запрещён');
});

document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        showViolation('Покидать вкладку во время теста нельзя');
    }
});

window.addEventListener('resize', () => {
    showViolation('Изменение размера окна запрещено');
});

document.addEventListener('copy', e => {
    e.preventDefault();
    showViolation('Копирование запрещено');
});

document.addEventListener('cut', e => {
    e.preventDefault();
    showViolation('Вырезание запрещено');
});

document.addEventListener('paste', e => {
    e.preventDefault();
    showViolation('Вставка запрещена');
});

document.addEventListener('keydown', e => {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        showViolation('Печать страницы запрещена');
    }
});

window.addEventListener('beforeprint', e => {
    e.preventDefault();
    showViolation('Печать экрана запрещена');
});

window.addEventListener('offline', () => showViolation('Нет сети во время теста запрещено'));
window.addEventListener('online', () => Logger.log('online', 'Сеть восстановлена'));

window.addEventListener('blur', () => showViolation('Покидать окно теста запрещено'));
window.addEventListener('focus', () => Logger.log('focus', 'Вернулись в окно'));


const violationTimers = {
    distance: 0,
    rotation: 0,
    tilt: 0,
    multi_face: 0,
    no_face: 0,
    camera_denied: 0,
};

const TEXT_TO_KEY = {
    "❌ Расстояние": "distance",
    "❌ Поворот головы": "rotation",
    "❌ Наклон вниз": "tilt",
    "❌ Несколько лиц в кадре": "multi_face",
    "❌ Лицо не найдено": "no_face",
    "🚫 Нет доступа к камере": "camera_denied"
};

const VIOLATION_THRESHOLD_MS = 2000; // 2 секунды
let lastViolationCheck = Date.now();

window.addEventListener('message', function (event) {
    const {type, data} = event.data || {};

    if (type === 'checklist_update' && Array.isArray(data.violations)) {
        const now = Date.now();
        const elapsed = now - lastViolationCheck;
        lastViolationCheck = now;

        const activeKeys = new Set();

        for (const text of data.violations) {
            const key = TEXT_TO_KEY[text];
            if (!key) continue;

            activeKeys.add(key);

            if (!violationTimers[key]) violationTimers[key] = 0;
            violationTimers[key] += elapsed;

            if (violationTimers[key] >= VIOLATION_THRESHOLD_MS) {
                Logger.log('violation', `Нарушение: ${text} >2 сек`);
                violationTimers[key] = 0;
            }
        }

        // Обнуляем неактивные таймеры
        for (const key of Object.keys(violationTimers)) {
            if (!activeKeys.has(key)) {
                violationTimers[key] = 0;
            }
        }
    }
});


