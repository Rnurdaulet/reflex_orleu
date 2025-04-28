(function () {
    'use strict';

    const LOG_KEY = 'quizViolationsLog';  // ключ в localStorage
    if (localStorage.getItem('quizViolationsLog')) {
        localStorage.removeItem('quizViolationsLog');
    }
    let logs = loadLogs();                // текущий массив логов

    // --- Утилиты для работы с localStorage ---
    function loadLogs() {
        try {
            const raw = localStorage.getItem(LOG_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch {
            return [];
        }
    }

    function saveLogs() {
        localStorage.setItem(LOG_KEY, JSON.stringify(logs));
    }

    window.logEvent = function (type, detail = '') {
        const entry = {
            event: type,
            detail: detail,
            timestamp: new Date().toISOString()
        };
        logs.push(entry);
        saveLogs();
        console.debug('Logged:', entry);
    };

    // --- Логируем открытие страницы сразу при загрузке ---
    logEvent('page_opened');

    // --- Подготовка уведомления (Bootstrap-toast) ---
    const toastEl = document.getElementById('violationToast');
    const toast = bootstrap.Toast.getOrCreateInstance(toastEl);

    window.showViolation = function (msg) {
        toastEl.querySelector('.toast-body').textContent = msg;
        toast.show();
        logEvent('violation', msg);
    };


    // --- Обработчики запрещённых действий ---
    // 1) Правый клик
    document.addEventListener('contextmenu', e => {
        e.preventDefault();
        showViolation('Правый клик запрещён');
    });

    // 2) Клавиши: копирование, DevTools, просмотр источников
    // document.addEventListener('keydown', e => {
    //     const k = e.key;
    //     const forbidden = k === 'F12'
    //     if (forbidden) {
    //         e.preventDefault();
    //         showViolation('DevTools запрещены');
    //     }});

    // 3) Смена вкладки
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            showViolation('Покидать вкладку во время теста нельзя');
        }
    });
    window.addEventListener('resize', () => {
        showViolation('Изменение размера окна запрещено');
    });
    // Блокируем прямое копирование буфера
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
    window.addEventListener('online', () => logEvent('online', 'Сеть восстановлена'));

    window.addEventListener('blur', () => showViolation('Покидать окно теста запрещено'));
    window.addEventListener('focus', () => logEvent('focus', 'Вернулись в окно'));


    // --- Для ручного просмотра логов в консоли ---
    window.getViolationLogs = () => loadLogs();

})();
