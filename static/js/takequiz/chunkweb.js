let chunkIndex = 0;
let chunkTimer;
let isRecording = false;

async function uploadChunk(blob) {
    try {
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
        console.log(`☁️ Залит чанк #${chunkIndex} в ${key}`);
        chunkIndex++;
    } catch (err) {
        console.error("❌ Ошибка загрузки чанка:", err);
    }
}

function recordChunk(video, log, checklist, violationToast, audioStream) {
    const canvas = document.createElement('canvas');
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d', {willReadFrequently: true});

    const draw = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        ctx.font = "9px monospace";
        ctx.fillStyle = "rgba(0,0,0,0.6)";
        ctx.fillRect(0, 0, 320, 60);

        ctx.fillStyle = "lime";
        ctx.fillText(log?.textContent || '', 10, 15);

        ctx.fillStyle = "red";
        ctx.fillText(violationToast?.textContent || '', 10, 30);

        ctx.fillStyle = "yellow";
        const lines = (checklist?.textContent || '').split("<br>");
        lines.forEach((line, i) => {
            ctx.fillText(line, 10, 45 + i * 12);
        });

        requestAnimationFrame(draw);
    };
    draw();

    const canvasStream = canvas.captureStream(10);
    const combinedStream = new MediaStream([
        ...canvasStream.getVideoTracks(),
        ...audioStream.getAudioTracks()
    ]);

    const recorder = new MediaRecorder(combinedStream, {mimeType: 'video/webm'});
    const chunks = [];

    recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
    };

    recorder.onstop = () => {
        const blob = new Blob(chunks, {type: 'video/webm'});
        uploadChunk(blob);
    };

    recorder.start();
    setTimeout(() => recorder.stop(), 20000);
}

async function startRecording() {
    const iframe = document.getElementById('proctorFrame');
    const iframeDoc = iframe.contentWindow.document;

    const video = iframeDoc.getElementById('video');
    const log = iframeDoc.getElementById('log');
    const checklist = iframeDoc.getElementById('checklist');
    const violationToast = iframeDoc.getElementById('violationToastbody');

    if (!video) {
        console.warn("⚠️ Видео внутри iframe не найдено");
        return;
    }

    const audioStream = await navigator.mediaDevices.getUserMedia({audio: true});

    isRecording = true;
    console.log("🔴 Запись началась");

    // ⏺️ Первый чанк
    recordChunk(video, log, checklist, violationToast, audioStream);

    // ⏱️ Каждые 20 секунд
    chunkTimer = setInterval(() => {
        if (isRecording) {
            recordChunk(video, log, checklist, violationToast, audioStream);
        }
    }, 20000);
}

// 🛑 Остановка при выходе
window.addEventListener('beforeunload', () => {
    if (isRecording) {
        console.log("⚠️ beforeunload: завершаем запись");
        clearInterval(chunkTimer);
        isRecording = false;
    }
});

// 🚀 Старт при загрузке iframe
document.getElementById('proctorFrame').addEventListener('load', () => {
    startRecording();
});