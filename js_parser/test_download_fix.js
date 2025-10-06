const fs = require('fs');
const path = require('path');

// Создаем тестовый файл
const testFileName = 'test_file_А123456_2024-01-15.pdf';
const testFilePath = path.join(__dirname, 'files', testFileName);

// Создаем папку files если её нет
const filesDir = path.join(__dirname, 'files');
if (!fs.existsSync(filesDir)) {
    fs.mkdirSync(filesDir, { recursive: true });
}

// Создаем тестовый файл
const testContent = 'Это тестовый PDF файл с кириллическими символами в имени';
fs.writeFileSync(testFilePath, testContent);

console.log('✅ Тестовый файл создан:', testFilePath);
console.log('📁 Размер файла:', fs.statSync(testFilePath).size, 'байт');

// Тестируем API endpoints
const express = require('express');
const app = express();

const FILES_DIR = path.join(__dirname, 'files');

app.get('/api/files', (req, res) => {
    try {
        const files = fs.readdirSync(FILES_DIR).filter(file => {
            const filePath = path.join(FILES_DIR, file);
            return fs.statSync(filePath).isFile();
        });
        res.json({ files });
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

const PORT = 3001;
app.listen(PORT, () => {
    console.log(`🚀 Тестовый сервер запущен на порту ${PORT}`);
    console.log(`📱 Откройте: http://localhost:${PORT}/api/files`);
    console.log(`📥 Тестовый файл: http://localhost:${PORT}/api/download/${encodeURIComponent(testFileName)}`);
    console.log(`ℹ️  Информация о файле: http://localhost:${PORT}/api/file-info/${encodeURIComponent(testFileName)}`);
});
