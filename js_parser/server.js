const express = require('express');
const path = require('path');
const fs = require('fs-extra');
const cors = require('cors');
const http = require('http');
const socketIo = require('socket.io');
const KadArbitrParser = require('./src/parser/KadArbitrParser');
const fetch = global.fetch || require('node-fetch');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.PORT || 3000;
const FILES_DIR = path.join(__dirname, 'files');
const CONFIG_PATH = path.join(__dirname, 'public', 'backend.config.json');
let BACKEND_BASE_URL = process.env.BACKEND_BASE_URL || 'http://91.224.87.134:8000';

// Загрузка конфигурации backend
try {
  if (fs.existsSync(CONFIG_PATH)) {
    const cfg = fs.readJsonSync(CONFIG_PATH);
    if (!process.env.BACKEND_BASE_URL && cfg && typeof cfg.backendBaseUrl === 'string' && cfg.backendBaseUrl.trim()) {
      BACKEND_BASE_URL = cfg.backendBaseUrl.trim().replace(/\/$/, '');
    }
  }
  console.log(`⚙️  BACKEND_BASE_URL: ${BACKEND_BASE_URL}`);
} catch (e) {
  console.warn('⚠️ Не удалось загрузить backend.config.json, используем дефолт:', e.message);
}

// Глобальные переменные
let parser = null;
let isProcessing = false;
let currentCase = '';
let progress = '';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));
app.use('/files', express.static(FILES_DIR));

// Создаем папку files если её нет
fs.ensureDirSync(FILES_DIR);

// Инициализация парсера
async function initializeParser() {
  try {
    console.log('🔧 Инициализация парсера...');
    parser = new KadArbitrParser();
    console.log('✅ Парсер инициализирован');
  } catch (error) {
    console.error('❌ Ошибка инициализации парсера:', error);
  }
}

// Очистка папки files
async function cleanupFiles() {
  try {
    await fs.emptyDir(FILES_DIR);
    console.log('✅ Папка files очищена');
  } catch (error) {
    console.error('❌ Ошибка очистки папки files:', error);
  }
}

// Маршруты
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/files', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'files.html'));
});

app.get('/diagnostics', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'diagnostics.html'));
});

// API маршруты
app.post('/api/parse', async (req, res) => {
  const { case_number } = req.body;
  
  if (isProcessing) {
    return res.status(429).json({
      success: false,
      message: 'Парсинг уже выполняется. Пожалуйста, подождите.'
    });
  }
  
  if (!case_number || !case_number.trim()) {
    return res.status(400).json({
      success: false,
      message: 'Номер дела не может быть пустым'
    });
  }
  
  isProcessing = true;
  currentCase = case_number.trim();
  progress = 'Начинаем парсинг...';
  
  // Уведомляем клиентов о начале парсинга
  io.emit('parsing_started', { case_number: currentCase, progress });
  
  try {
    // Очищаем папку files
    await cleanupFiles();
    
    // Выполняем парсинг
    const downloadedFiles = await parser.parseCase(case_number.trim(), (status) => {
      progress = status;
      io.emit('parsing_progress', { case_number: currentCase, progress });
    });
    
    progress = `Парсинг завершен. Скачано файлов: ${downloadedFiles.length}`;
    
    const result = {
      success: true,
      message: `Успешно скачано ${downloadedFiles.length} файлов`,
      files: downloadedFiles,
      case_number: currentCase
    };
    
    io.emit('parsing_completed', result);
    res.json(result);
    
  } catch (error) {
    console.error('Ошибка парсинга:', error);
    progress = `Ошибка: ${error.message}`;
    
    const result = {
      success: false,
      message: `Ошибка парсинга: ${error.message}`,
      files: [],
      case_number: currentCase
    };
    
    io.emit('parsing_error', result);
    res.status(500).json(result);
    
  } finally {
    isProcessing = false;
    currentCase = '';
    progress = '';
  }
});

app.get('/api/status', (req, res) => {
  res.json({
    is_parsing: isProcessing,
    current_case: currentCase,
    progress: progress
  });
});

app.get('/api/files', async (req, res) => {
  try {
    const files = await fs.readdir(FILES_DIR);
    const pdfFiles = files.filter(file => file.toLowerCase().endsWith('.pdf'));
    res.json({ files: pdfFiles });
  } catch (error) {
    console.error('Ошибка получения списка файлов:', error);
    res.json({ files: [] });
  }
});

app.get('/api/download/:filename', (req, res) => {
  const filename = decodeURIComponent(req.params.filename);
  const filePath = path.join(FILES_DIR, filename);
  
  console.log(`🔍 Запрос на скачивание файла: ${filename}`);
  console.log(`📁 Путь к файлу: ${filePath}`);
  
  if (!fs.existsSync(filePath)) {
    console.log(`❌ Файл не найден: ${filePath}`);
    return res.status(404).json({ message: 'Файл не найден' });
  }
  
  console.log(`✅ Файл найден, начинаем скачивание: ${filename}`);
  res.download(filePath, filename);
});

app.get('/api/file-info/:filename', (req, res) => {
  const filename = decodeURIComponent(req.params.filename);
  const filePath = path.join(FILES_DIR, filename);
  
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ message: 'Файл не найден' });
  }
  
  const stats = fs.statSync(filePath);
  res.json({
    name: filename,
    size: stats.size,
    created: stats.birthtime.toISOString(),
    modified: stats.mtime.toISOString()
  });
});

app.post('/api/clear', async (req, res) => {
  if (isProcessing) {
    return res.status(429).json({
      success: false,
      message: 'Нельзя очистить файлы во время парсинга'
    });
  }
  
  try {
    await cleanupFiles();
    res.json({ success: true, message: 'Файлы успешно удалены' });
  } catch (error) {
    console.error('Ошибка очистки файлов:', error);
    res.status(500).json({ success: false, message: 'Ошибка очистки файлов' });
  }
});

app.get('/api/doc-links', async (req, res) => {
  const caseNumber = req.query.case;
  if (!caseNumber) {
    return res.status(400).json({ message: 'Не указан номер дела' });
  }
  try {
    const backendResponse = await fetch(`${BACKEND_BASE_URL}/api/doc-links?case=${encodeURIComponent(caseNumber)}`);
    const data = await backendResponse.json();
    res.json(data);
  } catch (error) {
    console.error('Ошибка получения ссылок с бэкенда:', error);
    res.status(500).json({ message: 'Ошибка получения ссылок' });
  }
});

app.get('/api/cases', async (req, res) => {
  try {
    const backendResponse = await fetch(`${BACKEND_BASE_URL}/api/cases`);
    const data = await backendResponse.json();
    res.json(data);
  } catch (error) {
    console.error('Ошибка получения списка дел с бэкенда:', error);
    res.status(500).json({ message: 'Ошибка получения списка дел' });
  }
});

app.post('/api/test-browser', async (req, res) => {
  try {
    const testParser = new KadArbitrParser();
    const browserAvailable = await testParser.initBrowser();
    
    if (browserAvailable) {
      await testParser.closeBrowser();
      res.json({
        available: true,
        puppeteerVersion: require('puppeteer/package.json').version
      });
    } else {
      res.json({
        available: false,
        error: 'Не удалось инициализировать браузер'
      });
    }
  } catch (error) {
    res.json({
      available: false,
      error: error.message
    });
  }
});

// WebSocket соединения
io.on('connection', (socket) => {
  console.log('👤 Клиент подключен:', socket.id);
  
  // Отправляем текущий статус новому клиенту
  socket.emit('status_update', {
    is_parsing: isProcessing,
    current_case: currentCase,
    progress: progress
  });
  
  socket.on('disconnect', () => {
    console.log('👤 Клиент отключен:', socket.id);
  });
});

// Обработка ошибок
process.on('uncaughtException', (error) => {
  console.error('❌ Необработанная ошибка:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Необработанное отклонение промиса:', reason);
});

// Запуск сервера
async function startServer() {
  try {
    await initializeParser();
    
    server.listen(PORT, () => {
      console.log('🚀 Сервер запущен');
      console.log(`📱 Веб-интерфейс: http://localhost:${PORT}`);
      console.log(`⏹️  Для остановки: Ctrl+C`);
    });
  } catch (error) {
    console.error('❌ Ошибка запуска сервера:', error);
    process.exit(1);
  }
}

startServer();
