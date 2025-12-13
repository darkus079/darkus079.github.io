# 🚀 Деплой Telegram-бота на сервер

## 📋 Информация о сервере

| Параметр | Значение |
|----------|----------|
| **IP-адрес** | `213.171.25.83` |
| **ОС** | Ubuntu 22.04 |
| **Пользователь** | `user1` |
| **Путь к проекту** | `/home/user1/darkus079.github.io` |
| **Права** | sudo доступен ✅ |

---

## 📋 Содержание

1. [Подключение к серверу](#1-подключение-к-серверу)
2. [Подготовка системы](#2-подготовка-системы)
3. [Установка Python](#3-установка-python)
4. [Установка Java и Kafka](#4-установка-java-и-kafka)
5. [Установка Chrome](#5-установка-chrome)
6. [Настройка проекта](#6-настройка-проекта)
7. [Настройка автозапуска](#7-настройка-автозапуска-systemd)
8. [Запуск и проверка](#8-запуск-и-проверка)
9. [Обновление кода](#9-обновление-кода)

---

## 1. Подключение к серверу

```bash
ssh user1@213.171.25.83
```

---

## 2. Подготовка системы

### 2.1 Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.2 Установка базовых утилит

```bash
sudo apt install -y \
    curl wget git htop nano vim unzip zip \
    build-essential libssl-dev libffi-dev \
    software-properties-common apt-transport-https \
    ca-certificates gnupg lsb-release
```

### 2.3 Настройка локали

```bash
sudo locale-gen ru_RU.UTF-8
sudo update-locale LANG=ru_RU.UTF-8
```

### 2.4 Настройка часового пояса

```bash
sudo timedatectl set-timezone Europe/Moscow
```

---

## 3. Установка Python

### 3.1 Установка Python 3.11

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
```

### 3.2 Проверка

```bash
python3.11 --version
# Python 3.11.x
```

---

## 4. Установка Java и Kafka

### 4.1 Установка Java

```bash
sudo apt install -y openjdk-11-jdk

# Проверка
java -version
```

### 4.2 Установка Kafka

```bash
cd /opt
sudo wget https://archive.apache.org/dist/kafka/3.6.2/kafka_2.13-3.6.2.tgz
sudo tar -xzf kafka_2.13-3.6.2.tgz
sudo mv kafka_2.13-3.6.2 kafka
sudo rm kafka_2.13-3.6.2.tgz

# Права для user1
sudo chown -R user1:user1 /opt/kafka

# Создаём директории для данных
sudo mkdir -p /var/lib/kafka-logs /var/lib/zookeeper
sudo chown -R user1:user1 /var/lib/kafka-logs /var/lib/zookeeper
```

### 4.3 Настройка ZooKeeper

```bash
sudo nano /opt/kafka/config/zookeeper.properties
```

Содержимое:
```properties
dataDir=/var/lib/zookeeper
clientPort=2181
maxClientCnxns=60
admin.enableServer=false
```

### 4.4 Настройка Kafka

```bash
sudo nano /opt/kafka/config/server.properties
```

Измените:
```properties
broker.id=0
listeners=PLAINTEXT://localhost:9092
advertised.listeners=PLAINTEXT://localhost:9092
log.dirs=/var/lib/kafka-logs
zookeeper.connect=localhost:2181
auto.create.topics.enable=true
```

### 4.5 Systemd сервис для ZooKeeper

```bash
sudo nano /etc/systemd/system/zookeeper.service
```

```ini
[Unit]
Description=Apache ZooKeeper
After=network.target

[Service]
Type=simple
User=user1
ExecStart=/opt/kafka/bin/zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties
ExecStop=/opt/kafka/bin/zookeeper-server-stop.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.6 Systemd сервис для Kafka

```bash
sudo nano /etc/systemd/system/kafka.service
```

```ini
[Unit]
Description=Apache Kafka
After=network.target zookeeper.service
Requires=zookeeper.service

[Service]
Type=simple
User=user1
Environment="KAFKA_HEAP_OPTS=-Xmx512M -Xms512M"
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.7 Запуск Kafka

```bash
sudo systemctl daemon-reload
sudo systemctl enable zookeeper kafka
sudo systemctl start zookeeper
sleep 10
sudo systemctl start kafka

# Проверка статуса
sudo systemctl status zookeeper kafka
```

### 4.8 Проверка что Kafka работает (ВАЖНО!)

**Перед созданием топика убедитесь что Kafka запущена:**

```bash
# 1. Проверьте статус сервисов
sudo systemctl status zookeeper
sudo systemctl status kafka

# 2. Проверьте что порты открыты
ss -tlnp | grep -E "2181|9092"
# Должно быть:
# LISTEN  0  50  *:2181  *:*
# LISTEN  0  50  *:9092  *:*

# 3. Если порты не слушаются - смотрим логи
sudo journalctl -u zookeeper -n 50
sudo journalctl -u kafka -n 50
```

**Если Kafka не запускается:**

```bash
# Попробуйте запустить вручную (увидите ошибки)
/opt/kafka/bin/zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties &
sleep 10
/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties

# Частые проблемы:
# 1. Нет прав на директории - исправляем:
sudo mkdir -p /var/lib/kafka-logs /var/lib/zookeeper
sudo chown -R user1:user1 /var/lib/kafka-logs /var/lib/zookeeper /opt/kafka

# 2. Порт занят - проверяем:
sudo lsof -i :9092
sudo lsof -i :2181

# 3. Недостаточно памяти - уменьшаем heap:
# В /etc/systemd/system/kafka.service измените:
# Environment="KAFKA_HEAP_OPTS=-Xmx256M -Xms256M"
```

**Ждём пока Kafka полностью запустится (15-30 секунд):**

```bash
# Перезапуск
sudo systemctl restart zookeeper
sleep 15
sudo systemctl restart kafka
sleep 15

# Проверка подключения
/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092
# Если видите список версий API - Kafka работает!
```

### 4.9 Создание топика

**Только после того как Kafka работает:**

```bash
# Проверяем подключение
/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# Создаём топик
/opt/kafka/bin/kafka-topics.sh --create \
    --bootstrap-server localhost:9092 \
    --topic parsing-tasks \
    --partitions 3 \
    --replication-factor 1

# Проверка
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
# Должно вывести: parsing-tasks
```

---

## 5. Установка Chrome

### 5.1 Установка Google Chrome

```bash
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

sudo apt update
sudo apt install -y google-chrome-stable

# Проверка
google-chrome --version
```

### 5.2 Установка ChromeDriver

```bash
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+' | head -1)
CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}")

cd /tmp
wget "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip"
unzip chromedriver-linux64.zip
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

# Проверка
chromedriver --version
```

### 5.3 Установка Xvfb (виртуальный дисплей)

```bash
sudo apt install -y xvfb

# Тест Chrome
xvfb-run google-chrome --headless --no-sandbox --dump-dom https://example.com | head -5
```

---

## 6. Настройка проекта

### 6.1 Переход в директорию проекта

```bash
cd /home/user1/darkus079.github.io/tg_bot
```

### 6.2 Создание виртуального окружения

```bash
python3.11 -m venv venv

# Активация (используйте один из вариантов):
# Вариант 1 - для sh:
. venv/bin/activate

# Вариант 2 - для bash:
# bash
# source venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r ../backend/requirements.txt
```

### 6.3 Настройка .env

```bash
cp .env.example .env
nano .env
```

Заполните:
```env
TELEGRAM_BOT_TOKEN=ваш_токен
ADMIN_IDS=[ваш_id]
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_PARSING_TOPIC=parsing-tasks
LOG_LEVEL=INFO
```

### 6.4 Проверка

```bash
python -c "from src.config import settings; print('✅ Конфиг загружен')"
```

---

## 7. Настройка автозапуска (systemd)

### 7.1 Сервис для бота

```bash
sudo nano /etc/systemd/system/tgbot.service
```

```ini
[Unit]
Description=Telegram Bot
After=network.target kafka.service
Wants=kafka.service

[Service]
Type=simple
User=user1
WorkingDirectory=/home/user1/darkus079.github.io/tg_bot
Environment="PATH=/home/user1/darkus079.github.io/tg_bot/venv/bin:/usr/local/bin:/usr/bin"
Environment="PYTHONPATH=/home/user1/darkus079.github.io:/home/user1/darkus079.github.io/backend:/home/user1/darkus079.github.io/tg_bot:/home/user1/darkus079.github.io/tg_bot/src"
ExecStart=/home/user1/darkus079.github.io/tg_bot/venv/bin/python run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 7.2 Скрипт запуска Worker

```bash
nano /home/user1/darkus079.github.io/tg_bot/start_worker_xvfb.sh
```

```bash
#!/bin/bash
export DISPLAY=:99
export PYTHONPATH=/home/user1/darkus079.github.io:/home/user1/darkus079.github.io/backend:/home/user1/darkus079.github.io/tg_bot:/home/user1/darkus079.github.io/tg_bot/src

# Запуск Xvfb
if ! pgrep -x "Xvfb" > /dev/null; then
    Xvfb :99 -screen 0 1920x1080x24 &
    sleep 2
fi

cd /home/user1/darkus079.github.io/tg_bot
. venv/bin/activate
exec python start_worker.py
```

```bash
chmod +x /home/user1/darkus079.github.io/tg_bot/start_worker_xvfb.sh
```

### 7.3 Сервис для Worker

```bash
sudo nano /etc/systemd/system/tgbot-worker.service
```

```ini
[Unit]
Description=Telegram Bot Worker
After=network.target kafka.service tgbot.service
Wants=kafka.service

[Service]
Type=simple
User=user1
WorkingDirectory=/home/user1/darkus079.github.io/tg_bot
ExecStart=/home/user1/darkus079.github.io/tg_bot/start_worker_xvfb.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 7.4 Активация сервисов

```bash
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable tgbot tgbot-worker

# Запускаем
sudo systemctl start tgbot
sudo systemctl start tgbot-worker

# Проверка
sudo systemctl status tgbot tgbot-worker
```

---

## 8. Запуск и проверка

### 8.1 Проверка всех сервисов

```bash
# Статус
sudo systemctl status zookeeper kafka tgbot tgbot-worker

# Порты
ss -tlnp | grep -E "2181|9092"
```

### 8.2 Просмотр логов

```bash
# Логи бота
sudo journalctl -u tgbot -f

# Логи worker
sudo journalctl -u tgbot-worker -f

# Логи Kafka
sudo journalctl -u kafka -f
```

### 8.3 Тест бота

1. Откройте Telegram
2. Найдите бота
3. Отправьте `/start`
4. Отправьте номер дела: `А50-5568/08`

---

## 📝 Быстрые команды

```bash
# Подключение
ssh user1@213.171.25.83

# Перезапуск всего
sudo systemctl restart zookeeper kafka tgbot tgbot-worker

# Статус
sudo systemctl status tgbot tgbot-worker kafka zookeeper

# Логи бота
sudo journalctl -u tgbot -f

# Логи worker
sudo journalctl -u tgbot-worker -f

# Остановка
sudo systemctl stop tgbot tgbot-worker
```

---

## 9. Обновление кода

### 9.1 Обновление из Git репозитория

```bash
# Подключаемся к серверу
ssh user1@213.171.25.83

# Переходим в директорию проекта
cd /home/user1/darkus079.github.io

# Сохраняем локальные изменения (если есть)
git stash

# Получаем изменения из репозитория
git pull origin main

# Восстанавливаем локальные изменения (если нужно)
git stash pop
```

### 9.2 Обновление зависимостей (если изменились)

```bash
cd /home/user1/darkus079.github.io/tg_bot
. venv/bin/activate

pip install -r requirements.txt
pip install -r ../backend/requirements.txt
```

### 9.3 Перезапуск сервисов

```bash
# Перезапуск бота и worker
sudo systemctl restart tgbot tgbot-worker

# Проверка статуса
sudo systemctl status tgbot tgbot-worker

# Проверка логов (убедиться что нет ошибок)
sudo journalctl -u tgbot -n 20
sudo journalctl -u tgbot-worker -n 20
```

### 9.4 Полный перезапуск (включая Kafka)

```bash
sudo systemctl restart zookeeper kafka tgbot tgbot-worker
```

### 9.5 Быстрое обновление (одной командой)

```bash
cd /home/user1/darkus079.github.io && \
git pull origin main && \
sudo systemctl restart tgbot tgbot-worker && \
sudo systemctl status tgbot tgbot-worker
```

### 9.6 Ручная загрузка файлов (без Git)

**С Windows через SCP:**
```powershell
# Один файл
scp D:\CODE\sinichka_python\github_pages\darkus079.github.io\tg_bot\src\worker.py user1@213.171.25.83:/home/user1/darkus079.github.io/tg_bot/src/

# Всю папку src
scp -r D:\CODE\sinichka_python\github_pages\darkus079.github.io\tg_bot\src user1@213.171.25.83:/home/user1/darkus079.github.io/tg_bot/
```

**Через WinSCP:**
1. Подключитесь к серверу (SFTP, 213.171.25.83, user1)
2. Перейдите в `/home/user1/darkus079.github.io/tg_bot`
3. Перетащите изменённые файлы
4. На сервере: `sudo systemctl restart tgbot tgbot-worker`

---

## 📋 Чеклист

- [ ] Система обновлена
- [ ] Python 3.11 установлен
- [ ] Java установлена
- [ ] Kafka установлена и запущена
- [ ] Топик `parsing-tasks` создан
- [ ] Chrome установлен
- [ ] ChromeDriver установлен
- [ ] Xvfb установлен
- [ ] Проект настроен (venv, зависимости, .env)
- [ ] Systemd сервисы созданы
- [ ] Автозапуск включён
- [ ] Бот отвечает в Telegram
- [ ] Worker обрабатывает задачи

---

**IP сервера:** 213.171.25.83  
**ОС:** Ubuntu 22.04  
**Путь к проекту:** /home/user1/darkus079.github.io  
**Дата:** Декабрь 2025

