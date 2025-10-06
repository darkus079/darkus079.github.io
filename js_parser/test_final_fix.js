const fs = require('fs');
const path = require('path');
const express = require('express');

// Создаем тестовый файл с кириллическими символами
const testFileName = 'А84-4753_2024_20251006_151647_1_Test_Document.pdf';
const testFilePath = path.join(__dirname, 'files', testFileName);

// Создаем папку files если её нет
const filesDir = path.join(__dirname, 'files');
if (!fs.existsSync(filesDir)) {
    fs.mkdirSync(filesDir, { recursive: true });
}

// Создаем тестовый файл
const testContent = 'Это тестовый PDF файл с кириллическими символами в имени для проверки исправлений';
fs.writeFileSync(testFilePath, testContent);

console.log('✅ Тестовый файл создан:', testFilePath);
console.log('📁 Размер файла:', fs.statSync(testFilePath).size, 'байт');

// Создаем Express приложение для тестирования
const app = express();

app.get('/api/files', (req, res) => {
    try {
        const files = fs.readdirSync(filesDir).filter(file => {
            const filePath = path.join(filesDir, file);
            return fs.statSync(filePath).isFile();
        });
        console.log('📁 API /api/files - возвращаем файлы:', files);
        res.json({ files });
    } catch (error) {
        console.error('❌ Ошибка получения списка файлов:', error);
        res.json({ files: [] });
    }
});

app.get('/api/download/:filename', (req, res) => {
    const filename = decodeURIComponent(req.params.filename);
    const filePath = path.join(filesDir, filename);
    
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
    const filePath = path.join(filesDir, filename);
    
    console.log(`ℹ️ Запрос информации о файле: ${filename}`);
    
    if (!fs.existsSync(filePath)) {
        console.log(`❌ Файл не найден: ${filePath}`);
        return res.status(404).json({ message: 'Файл не найден' });
    }
    
    const stats = fs.statSync(filePath);
    const info = {
        name: filename,
        size: stats.size,
        created: stats.birthtime.toISOString(),
        modified: stats.mtime.toISOString()
    };
    
    console.log(`✅ Информация о файле:`, info);
    res.json(info);
});

// Тестируем API endpoints
async function testAPI() {
    const baseUrl = 'http://localhost:3002';
    
    try {
        console.log('\n🧪 Тестирование API endpoints...');
        
        // Тест 1: Получение списка файлов
        console.log('\n1️⃣ Тестируем /api/files');
        const filesResponse = await fetch(`${baseUrl}/api/files`);
        const filesData = await filesResponse.json();
        console.log('📁 Список файлов:', filesData);
        
        if (filesData.files && filesData.files.length > 0) {
            const testFile = filesData.files[0];
            console.log('📄 Тестовый файл:', testFile, 'тип:', typeof testFile);
            
            // Тест 2: Получение информации о файле
            console.log('\n2️⃣ Тестируем /api/file-info');
            const infoResponse = await fetch(`${baseUrl}/api/file-info/${encodeURIComponent(testFile)}`);
            if (infoResponse.ok) {
                const infoData = await infoResponse.json();
                console.log('ℹ️ Информация о файле:', infoData);
            } else {
                console.log('❌ Ошибка получения информации о файле');
            }
            
            // Тест 3: Тестируем URL скачивания
            console.log('\n3️⃣ Тестируем URL скачивания');
            const downloadUrl = `${baseUrl}/api/download/${encodeURIComponent(testFile)}`;
            console.log('🔗 URL скачивания:', downloadUrl);
            
            // Проверяем, что URL не содержит [object Object]
            if (downloadUrl.includes('[object Object]') || downloadUrl.includes('%5Bobject%20Object%5D')) {
                console.log('❌ ОШИБКА: URL содержит [object Object]');
            } else {
                console.log('✅ URL скачивания корректен');
            }
        }
        
    } catch (error) {
        console.error('❌ Ошибка тестирования API:', error);
    }
}

const PORT = 3002;
app.listen(PORT, () => {
    console.log(`🚀 Тестовый сервер запущен на порту ${PORT}`);
    console.log(`📱 Откройте: http://localhost:${PORT}/api/files`);
    console.log(`📥 Тестовый файл: http://localhost:${PORT}/api/download/${encodeURIComponent(testFileName)}`);
    console.log(`ℹ️  Информация о файле: http://localhost:${PORT}/api/file-info/${encodeURIComponent(testFileName)}`);
    
    // Запускаем тесты через 2 секунды
    setTimeout(testAPI, 2000);
});
