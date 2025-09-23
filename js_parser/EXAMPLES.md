# 📚 Примеры использования парсера kad.arbitr.ru

## 🎯 Основные сценарии использования

### 1. Поиск дела по номеру

**Входные данные:**
```
Номер дела: А81-8566/2025
```

**Ожидаемый результат:**
- Найденное дело отображается в результатах
- PDF файлы автоматически скачиваются
- Показывается уведомление об успехе

### 2. Поиск дела с ошибкой

**Входные данные:**
```
Номер дела: А81-9999/2025 (несуществующий)
```

**Ожидаемый результат:**
- Показывается ошибка "Дела не найдены"
- Отображаются советы по устранению
- Форма разблокируется для повторного ввода

### 3. Поиск дела с сетевыми проблемами

**Сценарий:**
- Медленное интернет соединение
- Временная недоступность сайта

**Ожидаемый результат:**
- Показывается прогресс загрузки
- При ошибке - fallback механизм
- Советы по устранению проблем

## 📋 Примеры номеров дел

### Арбитражные дела

```
А81-8566/2025    # Московский арбитражный суд
А40-123456/2024  # Арбитражный суд г. Москвы
А50-98765/2025   # Арбитражный суд Пермского края
А41-111111/2024  # Арбитражный суд Московской области
А42-222222/2025  # Арбитражный суд Кемеровской области
```

### Форматы номеров

```
А81-8566/2025     # Стандартный формат
А81-8566/25       # Сокращенный год
А81-8566/2025     # Полный год
А81-8566-2025     # С дефисом вместо слеша
```

## 🔧 Технические примеры

### Использование API

```javascript
// Создание экземпляра парсера
const parser = new KadArbitrParser();

// Парсинг дела
parser.parseCase('А81-8566/2025', (progress) => {
    console.log('Прогресс:', progress);
}).then(files => {
    console.log('Скачано файлов:', files.length);
}).catch(error => {
    console.error('Ошибка:', error.message);
});
```

### Обработка ошибок

```javascript
try {
    const files = await parser.parseCase('А81-8566/2025');
    console.log('Успех:', files);
} catch (error) {
    if (error.message.includes('не найдены')) {
        console.log('Дело не найдено');
    } else if (error.message.includes('CORS')) {
        console.log('Проблема с сетью');
    } else {
        console.log('Неизвестная ошибка');
    }
}
```

### Настройка логирования

```javascript
// Получение логов
const logger = new Logger();
logger.info('Начало работы');
logger.warn('Предупреждение');
logger.error('Ошибка');

// Просмотр всех логов
console.log(logger.logs);
```

## 🌐 Примеры для разных браузеров

### Chrome

```javascript
// Проверка поддержки функций
if (window.fetch && window.Blob && window.URL) {
    console.log('Браузер поддерживает все функции');
} else {
    console.log('Требуется обновление браузера');
}
```

### Firefox

```javascript
// Настройка для Firefox
const parser = new KadArbitrParser();
parser.corsProxy = 'https://cors-anywhere.herokuapp.com/';
```

### Safari

```javascript
// Проверка Safari
if (navigator.userAgent.includes('Safari')) {
    console.log('Используется Safari');
    // Дополнительные настройки для Safari
}
```

## 📱 Примеры для мобильных устройств

### Адаптация для мобильных

```css
/* Медиа-запросы для мобильных */
@media (max-width: 768px) {
    .container {
        padding: 20px;
        margin: 10px;
    }
    
    .form-input {
        font-size: 16px; /* Предотвращает зум на iOS */
    }
}
```

### Сенсорные события

```javascript
// Обработка сенсорных событий
document.addEventListener('touchstart', function(e) {
    console.log('Касание началось');
});

document.addEventListener('touchend', function(e) {
    console.log('Касание завершено');
});
```

## 🔒 Примеры безопасности

### Проверка HTTPS

```javascript
// Проверка безопасного соединения
if (location.protocol !== 'https:') {
    console.warn('Рекомендуется использовать HTTPS');
}
```

### Валидация входных данных

```javascript
// Простая валидация номера дела
function validateCaseNumber(caseNumber) {
    const pattern = /^А\d{2}-\d{4}\/\d{4}$/;
    return pattern.test(caseNumber);
}

// Использование
if (validateCaseNumber('А81-8566/2025')) {
    console.log('Номер дела корректен');
} else {
    console.log('Неверный формат номера дела');
}
```

## 📊 Примеры мониторинга

### Отслеживание использования

```javascript
// Счетчик использований
let usageCount = localStorage.getItem('usageCount') || 0;
usageCount++;
localStorage.setItem('usageCount', usageCount);

// Отправка статистики
fetch('/api/usage', {
    method: 'POST',
    body: JSON.stringify({ count: usageCount })
});
```

### Логирование ошибок

```javascript
// Отправка ошибок на сервер
function logError(error, context) {
    fetch('/api/errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            error: error.message,
            context: context,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent
        })
    });
}
```

## 🎨 Примеры кастомизации

### Изменение темы

```css
/* Темная тема */
.dark-theme {
    background: #1a1a1a;
    color: #ffffff;
}

.dark-theme .container {
    background: #2d2d2d;
    border: 1px solid #444;
}
```

### Добавление анимаций

```css
/* Анимация загрузки */
@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

.loading {
    animation: pulse 1s infinite;
}
```

## 🔄 Примеры автоматизации

### Автоматический парсинг

```javascript
// Парсинг списка дел
const caseNumbers = ['А81-8566/2025', 'А40-123456/2024', 'А50-98765/2025'];

async function parseMultipleCases() {
    for (const caseNumber of caseNumbers) {
        try {
            console.log(`Парсинг дела: ${caseNumber}`);
            const files = await parser.parseCase(caseNumber);
            console.log(`Скачано файлов: ${files.length}`);
            
            // Пауза между запросами
            await new Promise(resolve => setTimeout(resolve, 5000));
        } catch (error) {
            console.error(`Ошибка для дела ${caseNumber}:`, error.message);
        }
    }
}
```

### Планировщик задач

```javascript
// Парсинг по расписанию
function scheduleParsing(caseNumber, interval) {
    setInterval(async () => {
        try {
            const files = await parser.parseCase(caseNumber);
            console.log(`Плановый парсинг: ${files.length} файлов`);
        } catch (error) {
            console.error('Ошибка планового парсинга:', error);
        }
    }, interval);
}

// Парсинг каждые 30 минут
scheduleParsing('А81-8566/2025', 30 * 60 * 1000);
```

## 📝 Примеры документации

### JSDoc комментарии

```javascript
/**
 * Парсит дело по номеру
 * @param {string} caseNumber - Номер дела в формате А81-8566/2025
 * @param {function} progressCallback - Функция обратного вызова для прогресса
 * @returns {Promise<string[]>} Массив имен скачанных файлов
 * @throws {Error} Ошибка парсинга
 * @example
 * const files = await parser.parseCase('А81-8566/2025', (progress) => {
 *   console.log('Прогресс:', progress);
 * });
 */
async parseCase(caseNumber, progressCallback) {
    // Реализация
}
```

### README примеры

```markdown
## Быстрый старт

```javascript
// Создание парсера
const parser = new KadArbitrParser();

// Парсинг дела
parser.parseCase('А81-8566/2025')
  .then(files => console.log('Скачано:', files.length))
  .catch(error => console.error('Ошибка:', error));
```
```

---

**Эти примеры помогут вам быстро начать работу с парсером!** 🚀
