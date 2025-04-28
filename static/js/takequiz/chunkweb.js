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


    // === Верхняя панель ===
    ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
    ctx.fillRect(0, 0, canvas.width, 40);

    ctx.font = "12px monospace";
    ctx.fillStyle = "lime";
    ctx.textBaseline = "top";
    const timeStr = new Date().toLocaleTimeString();
    ctx.fillText(`[${timeStr}] ✅ ID: ${externalId}`, 10, 10);

    // === Нижняя панель для чек-листа ===
    ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
    ctx.fillRect(0, canvas.height - 60, canvas.width, 60);

    ctx.font = "11px monospace";
    ctx.textBaseline = "top";

    const padding = 10;
    const lineHeight = 14;
    let x = padding;
    let y = canvas.height - 50;

    // Разбиваем checklistText на отдельные фразы
    const checklistItems = checklistText.replace(/<br\s*\/?>/gi, '\n').split('\n').filter(Boolean);

    checklistItems.forEach((item) => {
        const cleanItem = item.trim();
        if (!cleanItem) return;

        ctx.fillStyle = cleanItem.includes('❌') ? "red" :
                        cleanItem.includes('✅') ? "lime" : "yellow";

        const words = cleanItem.split(' ');

        for (const word of words) {
            const measure = ctx.measureText(word + ' ');
            if (x + measure.width > canvas.width - padding) {
                x = padding;
                y += lineHeight;
            }
            ctx.fillText(word + ' ', x, y);
            x += measure.width;
        }
    });

    // === Рамка ===
    if (violation) {
        ctx.strokeStyle = "red";
        ctx.lineWidth = 5;
        ctx.strokeRect(0, 0, canvas.width, canvas.height);
    } else {
        ctx.strokeStyle = "lime";
        ctx.lineWidth = 2;
        ctx.strokeRect(0, 0, canvas.width, canvas.height);
    }

    requestAnimationFrame(draw);
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

function startChunkRecording(stream) {
    const recorder = new MediaRecorder(stream, {mimeType: 'video/webm'});

    recorder.ondataavailable = async (e) => {
        if (e.data.size > 0) {
            await uploadChunk(e.data);
        }
    };

    recorder.start(20000); // каждый чанк 20 сек
    console.log('🔴 Запись чанков началась');
    isRecording = true;
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
    badDistance: 0,
    badRotation: 0,
    badTilt: 0,
    multiFace: 0,
};

const VIOLATION_THRESHOLD_MS = 5000; // 5 секунд
let lastViolationCheck = Date.now();

// слушаем сообщения из iframe
window.addEventListener('message', function (event) {
    const {type, data} = event.data || {};

    if (type === 'checklist_update') {
        const now = Date.now();
        const elapsed = now - lastViolationCheck;
        lastViolationCheck = now;

        // Для всех известных нарушений
        for (let key of Object.keys(violationTimers)) {
            if (data.violations.includes(key)) {
                violationTimers[key] += elapsed;
            } else {
                violationTimers[key] = 0;
            }

            // Проверяем — если накопилось больше 5 секунд
            if (violationTimers[key] >= VIOLATION_THRESHOLD_MS) {
                Logger.log('violation', `Нарушение: ${key} >5 секунд`);
                violationTimers[key] = 0; // сбрасываем
            }
        }
    }
});

