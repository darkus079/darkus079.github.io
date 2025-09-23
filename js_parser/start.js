#!/usr/bin/env node
/**
 * Скрипт запуска парсера kad.arbitr.ru с веб-интерфейсом
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs-extra');

console.log('🚀 Запуск парсера kad.arbitr.ru (JavaScript версия)');
console.log('=' * 60);

// Проверяем наличие Node.js
const nodeVersion = process.version;
console.log(`📦 Node.js версия: ${nodeVersion}`);

if (parseInt(nodeVersion.slice(1).split('.')[0]) < 16) {
  console.error('❌ Требуется Node.js версии 16.0.0 или выше');
  process.exit(1);
}

// Проверяем наличие package.json
if (!fs.existsSync(path.join(__dirname, 'package.json'))) {
  console.error('❌ package.json не найден. Запустите из корневой папки проекта');
  process.exit(1);
}

// Создаем необходимые папки
const filesDir = path.join(__dirname, 'files');
fs.ensureDirSync(filesDir);
console.log('✅ Папка files создана');

// Проверяем зависимости
console.log('🔍 Проверка зависимостей...');
try {
  require('express');
  require('puppeteer');
  require('socket.io');
  console.log('✅ Основные зависимости найдены');
} catch (error) {
  console.error('❌ Отсутствуют зависимости:', error.message);
  console.log('📦 Установите зависимости: npm install');
  process.exit(1);
}

// Запускаем сервер
console.log('🌟 Запуск веб-сервера...');
console.log(`📱 Веб-интерфейс: http://localhost:3000`);
console.log(`⏹️  Для остановки: Ctrl+C`);
console.log('=' * 60);

// Небольшая задержка
setTimeout(() => {
  try {
    // Запускаем сервер
    const server = spawn('node', ['server.js'], {
      cwd: __dirname,
      stdio: 'inherit',
      shell: true
    });
    
    server.on('error', (error) => {
      console.error('❌ Ошибка запуска сервера:', error);
    });
    
    server.on('close', (code) => {
      console.log(`\n🛑 Сервер остановлен с кодом: ${code}`);
    });
    
    // Обработка Ctrl+C
    process.on('SIGINT', () => {
      console.log('\n\n🛑 Получен сигнал завершения');
      console.log('👋 Парсер остановлен');
      server.kill('SIGINT');
      process.exit(0);
    });
    
  } catch (error) {
    console.error('❌ Ошибка запуска:', error);
    process.exit(1);
  }
}, 1000);
