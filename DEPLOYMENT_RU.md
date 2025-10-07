## Деплой backend сервиса на Ubuntu 22.04 (IP 91.224.87.134)

Адрес ВМ: 91.224.87.134  • Пользователь: user1  • Протокол: HTTP (без TLS)  • Порт backend: 8000

Репозиторий проекта: [darkus079/darkus079.github.io](https://github.com/darkus079/darkus079.github.io)

### 1. Архитектура и взаимодействие Frontend/Backend

- Frontend размещается отдельно на GitHub Pages и обращается к Backend по публичному IP `http://91.224.87.134:8000`.
- CORS на Backend уже настроен на `https://darkus079.github.io`.
- Основные эндпоинты Backend (FastAPI):
  - `POST /api/parse` — поставить в очередь сбор ссылок по номеру дела
  - `GET /api/status` — текущий статус очереди/обработки
  - `GET /api/links?case=<НомерДела>` — получить собранные ссылки (PDF)
  - `GET /api/cases` — список дел, по которым есть ссылки
  - `GET /api/health` — health-check (здоровье сервиса)
  - `GET /diagnostics` — страница диагностики
- Типичный сценарий во Frontend:
  1) `POST /api/parse` с `{"case_number": "А81-..."}`
  2) опрос `GET /api/status` до завершения
  3) получение результатов `GET /api/links?case=...`

Примечание: Backend выполняет сбор ссылок и не хранит/отдаёт локальные файлы PDF. Очередь обрабатывается последовательно, что подходит под указанную нагрузку (до ~20 запросов, ~10 одновременных пользователей).

### 2. Предварительные условия

- ОС: Ubuntu 22.04 LTS
- Python 3.10 (системный) подходит
- Порт 8000 должен быть открыт на самой ВМ (UFW)

### 3. Подключение к серверу

```bash
ssh user1@91.224.87.134
```

### 4. Системные обновления и базовые пакеты

```bash
sudo apt update -y && sudo apt upgrade -y
sudo apt install -y git python3-venv python3-pip curl ca-certificates apt-transport-https gnupg
```

### 5. Установка Google Chrome (для Selenium/webdriver)

На сервере нужен браузер. Рекомендуется Google Chrome Stable:

```bash
wget -qO - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-linux.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update -y
sudo apt install -y google-chrome-stable

# Полезные системные библиотеки для headless-режима Chrome
sudo apt install -y libnss3 libxss1 libasound2 libatk1.0-0 libatk-bridge2.0-0 \
  libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxrandr2 \
  libcups2 libdrm2 libgbm1 libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
  fonts-liberation libu2f-udev
```

Примечание: `webdriver-manager` автоматически загрузит подходящий ChromeDriver под установленный браузер.

### 6. Загрузка проекта из Git

```bash
cd ~
git clone --depth=1 --branch main git@github.com:darkus079/darkus079.github.io.git
# Если на сервере нет SSH-ключей к GitHub, используйте HTTPS:
# git clone --depth=1 --branch main https://github.com/darkus079/darkus079.github.io.git
```

### 7. Создание виртуального окружения и установка зависимостей

```bash
cd ~/darkus079.github.io/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 8. Ручевой пробный запуск (проверка)

```bash
source ~/darkus079.github.io/backend/venv/bin/activate
cd ~/darkus079.github.io/backend
uvicorn backend_service:app --host 0.0.0.0 --port 8000
```

Проверьте из локальной машины:

```bash
curl http://91.224.87.134:8000/api/health
# Откройте в браузере: http://91.224.87.134:8000/docs
```

Остановите Ctrl+C и переходите к настройке автозапуска.

### 9. Настройка UFW (открытие порта 8000)

```bash
sudo ufw allow 8000/tcp
sudo ufw status verbose
# При необходимости включить UFW:
# sudo ufw enable
```

### 10. Установка часового пояса и локали

```bash
sudo timedatectl set-timezone Europe/Moscow
sudo update-locale LANG=ru_RU.UTF-8
```

### 11. Настройка systemd-сервиса

Создайте unit `/etc/systemd/system/kad-backend.service`:

```ini
[Unit]
Description=KAD Arbitr Backend (FastAPI + Uvicorn)
After=network-online.target
Wants=network-online.target

[Service]
User=user1
WorkingDirectory=/home/user1/darkus079.github.io/backend
Environment=PYTHONUNBUFFERED=1
Environment=TZ=Europe/Moscow
ExecStart=/home/user1/darkus079.github.io/backend/.venv/bin/uvicorn backend_service:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
Restart=always
RestartSec=5
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
```

Активируйте сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kad-backend.service
sudo systemctl start kad-backend.service
sudo systemctl status kad-backend.service --no-pager
```

Просмотр логов:

```bash
journalctl -u kad-backend.service -f --no-pager
```

### 12. Проверка доступности снаружи

```bash
curl http://91.224.87.134:8000/api/health
curl "http://91.224.87.134:8000/api/links?case=А81-8566/2025" --get
```

Откройте документацию API: `http://91.224.87.134:8000/docs`.

### 13. Настройка Frontend

- Frontend развёрнут на GitHub Pages и обращается к Backend по `http://91.224.87.134:8000`.
- В репозитории установлен базовый URL во `js_parser/js/backend-client.js`.
- CORS на Backend уже разрешает `https://darkus079.github.io`.

### 14. Обновления и деплой новых версий

```bash
ssh user1@91.224.87.134
cd ~/darkus079.github.io
git pull --rebase
cd backend
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart kad-backend.service
sudo systemctl status kad-backend.service --no-pager
```

### 15. Тестовый сценарий E2E

1) Откройте фронтенд на GitHub Pages, введите номер дела и запустите парсинг.
2) Наблюдайте прогресс (frontend опрашивает `/api/status`).
3) По завершении проверьте ссылки через `/api/links?case=...`.

### 16. Траблшутинг

- Порт 8000 недоступен:
  - Проверьте сервис: `systemctl status kad-backend` и логи `journalctl -u kad-backend -f`
  - Проверьте firewall: `sudo ufw status` (должен быть `8000/tcp ALLOW`)
  - Проверьте, что процесс слушает 0.0.0.0:8000: `ss -lntp | grep 8000`
- Chrome/ChromeDriver несоответствие:
  - Убедитесь, что установлен Google Chrome Stable
  - `webdriver-manager` скачает совместимый драйвер автоматически при первом запуске
- Ошибки CORS в браузере:
  - Проверьте, что обращение идёт с `https://darkus079.github.io`
  - Убедитесь, что Backend работает по `http://91.224.87.134:8000`
- Высокая нагрузка/очередь:
  - По умолчанию `--workers 1` (из-за последовательной логики парсинга и общей очереди)
  - Увеличение числа воркеров потребует пересмотра очереди/синхронизации

### 17. Изменения в коде, влияющие на деплой

- Backend переведён на биндинг `0.0.0.0:8000` (вместо `127.0.0.1`).
- Frontend (клиент) настроен на `http://91.224.87.134:8000`.
- Эндпоинт здоровья: `GET /api/health`; диагностика: `GET /diagnostics`.

Готово: после выполнения шагов из этого файла backend будет доступен по `http://91.224.87.134:8000`, а фронтенд GitHub Pages — по своему домену, с корректным CORS и маршрутом взаимодействия.


