/**
 * Клиентский парсер kad.arbitr.ru для GitHub Pages
 * Использует Playwright для автоматизации браузера
 */

class KadArbitrParser {
    constructor() {
        this.isProcessing = false;
        this.downloadedFiles = [];
        this.logger = new Logger();
        this.corsProxy = 'https://api.allorigins.win/raw?url=';
    }

    async parseCase(caseNumber, progressCallback) {
        if (this.isProcessing) {
            throw new Error('Парсер уже работает! Повторный запуск заблокирован!');
        }

        this.isProcessing = true;
        this.downloadedFiles = [];
        
        this.logger.info(`🚀 НАЧАЛО ПАРСИНГА: ${caseNumber}`);

        try {
            // Инициализируем Playwright
            if (progressCallback) progressCallback('Инициализация браузера...');
            this.logger.info('🔧 Инициализация браузера...');
            
            const { chromium } = await this.loadPlaywright();
            const browser = await chromium.launch({
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--window-size=1920,1080'
                ]
            });

            const context = await browser.newContext({
                viewport: { width: 1920, height: 1080 },
                userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            });

            const page = await context.newPage();
            
            // Маскировка автоматизации
            await page.addInitScript(() => {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                delete navigator.__proto__.webdriver;
                
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });
            });

            // Поиск дела
            if (progressCallback) progressCallback('Поиск дела...');
            this.logger.info('🔍 Поиск дела...');
            
            const caseLinks = await this.searchCase(page, caseNumber, progressCallback);
            
            if (caseLinks.length === 0) {
                throw new Error('Дела не найдены');
            }

            // Скачиваем файлы из первого найденного дела
            const caseUrl = caseLinks[0].url;
            this.logger.info(`🔄 Обработка дела: ${caseLinks[0].text}`);
            
            if (progressCallback) progressCallback('Скачивание файлов...');
            this.downloadedFiles = await this.downloadPdfFiles(page, caseUrl, caseNumber, progressCallback);

            await browser.close();
            
            this.logger.info(`✅ Обработка завершена. Скачано файлов: ${this.downloadedFiles.length}`);
            return this.downloadedFiles;

        } catch (error) {
            this.logger.error(`❌ Критическая ошибка парсинга: ${error.message}`);
            throw error;
        } finally {
            this.isProcessing = false;
        }
    }

    async loadPlaywright() {
        // Динамическая загрузка Playwright
        if (typeof window !== 'undefined') {
            // В браузере используем CDN
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://unpkg.com/playwright@1.40.0/lib/browser.js';
                script.onload = () => {
                    resolve(window.playwright);
                };
                script.onerror = () => {
                    // Fallback: используем fetch API
                    this.logger.warn('Playwright недоступен, используем fetch API');
                    resolve({ chromium: null });
                };
                document.head.appendChild(script);
            });
        } else {
            // В Node.js
            return require('playwright');
        }
    }

    async searchCase(page, caseNumber, progressCallback) {
        try {
            this.logger.info(`🎯 Поиск дела: ${caseNumber}`);
            
            if (progressCallback) progressCallback('Переход на сайт kad.arbitr.ru...');
            
            // Используем CORS proxy для обхода ограничений
            const proxyUrl = this.corsProxy + encodeURIComponent('https://kad.arbitr.ru/');
            
            // Переходим на сайт через proxy
            await page.goto(proxyUrl, { 
                waitUntil: 'networkidle',
                timeout: 30000 
            });
            
            await this.humanDelay(2, 4, 'ожидание загрузки главной страницы');
            
            if (progressCallback) progressCallback('Поиск поля ввода...');
            
            // Ищем поле поиска
            await page.waitForSelector('input[type="text"]', { timeout: 10000 });
            
            // Очищаем поле и вводим номер дела
            await page.click('input[type="text"]');
            await page.keyboard.press('Control+a');
            await page.type('input[type="text"]', caseNumber);
            
            await this.humanDelay(1, 2, 'ввод номера дела');
            
            if (progressCallback) progressCallback('Выполнение поиска...');
            
            // Нажимаем кнопку поиска
            await page.click('button[type="submit"]');
            
            // Ждем результатов поиска
            await page.waitForLoadState('networkidle', { timeout: 15000 });
            
            if (progressCallback) progressCallback('Анализ результатов поиска...');
            
            // Ищем ссылки на дела
            const caseLinks = await page.evaluate(() => {
                const links = [];
                const elements = document.querySelectorAll('a[href*="/card/"]');
                
                elements.forEach(element => {
                    const href = element.getAttribute('href');
                    const text = element.textContent.trim();
                    if (href && text) {
                        links.push({
                            url: href.startsWith('http') ? href : `https://kad.arbitr.ru${href}`,
                            text: text
                        });
                    }
                });
                
                return links;
            });
            
            if (caseLinks.length === 0) {
                throw new Error('Дела не найдены');
            }
            
            this.logger.info(`✅ Найдено дел: ${caseLinks.length}`);
            return caseLinks;
            
        } catch (error) {
            this.logger.error(`❌ Ошибка поиска дела: ${error.message}`);
            // Fallback: попробуем через fetch API
            return await this.searchCaseFallback(caseNumber, progressCallback);
        }
    }

    async searchCaseFallback(caseNumber, progressCallback) {
        try {
            this.logger.info('🔄 Используем fallback метод поиска...');
            
            if (progressCallback) progressCallback('Альтернативный поиск...');
            
            // Используем fetch API с CORS proxy
            const searchUrl = `https://kad.arbitr.ru/search?query=${encodeURIComponent(caseNumber)}`;
            const proxyUrl = this.corsProxy + encodeURIComponent(searchUrl);
            
            const response = await fetch(proxyUrl);
            const html = await response.text();
            
            // Парсим HTML для поиска ссылок
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const links = [];
            
            const elements = doc.querySelectorAll('a[href*="/card/"]');
            elements.forEach(element => {
                const href = element.getAttribute('href');
                const text = element.textContent.trim();
                if (href && text) {
                    links.push({
                        url: href.startsWith('http') ? href : `https://kad.arbitr.ru${href}`,
                        text: text
                    });
                }
            });
            
            if (links.length === 0) {
                throw new Error('Дела не найдены через fallback метод');
            }
            
            this.logger.info(`✅ Найдено дел через fallback: ${links.length}`);
            return links;
            
        } catch (error) {
            this.logger.error(`❌ Ошибка fallback поиска: ${error.message}`);
            throw new Error('Не удалось найти дела. Проверьте номер дела и попробуйте снова.');
        }
    }

    async downloadPdfFiles(page, caseUrl, caseNumber, progressCallback) {
        try {
            this.logger.info(`📁 Переход к делу: ${caseUrl}`);
            
            if (progressCallback) progressCallback('Переход к делу...');
            
            // Используем CORS proxy
            const proxyUrl = this.corsProxy + encodeURIComponent(caseUrl);
            await page.goto(proxyUrl, { 
                waitUntil: 'networkidle',
                timeout: 30000 
            });
            
            await this.humanDelay(2, 3, 'ожидание загрузки страницы дела');
            
            if (progressCallback) progressCallback('Поиск вкладки "Электронное дело"...');
            
            // Ищем вкладку "Электронное дело"
            try {
                await page.waitForSelector('div.b-case-chrono-button-text', { timeout: 10000 });
                
                // Ищем кнопку с текстом "Электронное дело"
                const electronicTab = await page.evaluateHandle(() => {
                    const buttons = Array.from(document.querySelectorAll('div.b-case-chrono-button-text'));
                    return buttons.find(btn => btn.textContent.includes('Электронное дело'));
                });
                
                if (electronicTab) {
                    await electronicTab.click();
                    this.logger.info('✅ Переход на вкладку "Электронное дело"');
                } else {
                    throw new Error('Вкладка "Электронное дело" не найдена');
                }
                
            } catch (error) {
                this.logger.warn('❌ Вкладка "Электронное дело" не найдена:', error);
                throw new Error('Вкладка "Электронное дело" недоступна');
            }
            
            await this.humanDelay(2, 3, 'ожидание загрузки списка документов');
            
            if (progressCallback) progressCallback('Поиск PDF документов...');
            
            // Ищем PDF ссылки
            const pdfLinks = await page.evaluate(() => {
                const links = [];
                const elements = document.querySelectorAll('a[href*=".pdf"], a[href*="document"]');
                
                elements.forEach(element => {
                    const href = element.getAttribute('href');
                    const text = element.textContent.trim();
                    if (href && text) {
                        links.push({
                            url: href.startsWith('http') ? href : `https://kad.arbitr.ru${href}`,
                            text: text
                        });
                    }
                });
                
                return links;
            });
            
            if (pdfLinks.length === 0) {
                throw new Error('PDF документы не найдены');
            }
            
            this.logger.info(`📄 Найдено PDF документов: ${pdfLinks.length}`);
            
            if (progressCallback) progressCallback(`Скачивание ${pdfLinks.length} документов...`);
            
            const downloadedFiles = [];
            
            // Скачиваем каждый PDF файл
            for (let i = 0; i < pdfLinks.length; i++) {
                const link = pdfLinks[i];
                
                try {
                    if (progressCallback) {
                        progressCallback(`Скачивание документа ${i + 1} из ${pdfLinks.length}...`);
                    }
                    
                    this.logger.info(`📥 Скачивание: ${link.text}`);
                    
                    // Создаем уникальное имя файла
                    const timestamp = new Date().toISOString().split('T')[0];
                    const filename = `${caseNumber}_${timestamp}_${i + 1}_${this.sanitizeFilename(link.text)}.pdf`;
                    
                    // Скачиваем файл через CORS proxy
                    const pdfProxyUrl = this.corsProxy + encodeURIComponent(link.url);
                    const response = await fetch(pdfProxyUrl);
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        
                        // Создаем ссылку для скачивания
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        
                        downloadedFiles.push(filename);
                        this.logger.info(`✅ Скачан: ${filename}`);
                    } else {
                        this.logger.warn(`❌ Ошибка скачивания: ${link.text}`);
                    }
                    
                    await this.humanDelay(1, 2, 'пауза между скачиваниями');
                    
                } catch (error) {
                    this.logger.error(`❌ Ошибка скачивания файла ${link.text}: ${error.message}`);
                }
            }
            
            this.logger.info(`✅ Скачано файлов: ${downloadedFiles.length}`);
            return downloadedFiles;
            
        } catch (error) {
            this.logger.error(`❌ Ошибка скачивания PDF файлов: ${error.message}`);
            throw error;
        }
    }

    sanitizeFilename(filename) {
        return filename
            .replace(/[<>:"/\\|?*]/g, '_')
            .replace(/\s+/g, '_')
            .substring(0, 100);
    }

    async humanDelay(min, max, description = '') {
        const delay = Math.floor(Math.random() * (max - min + 1)) + min;
        this.logger.info(`⏳ ${description} (${delay}с)`);
        await new Promise(resolve => setTimeout(resolve, delay * 1000));
    }
}

/**
 * Система логирования
 */
class Logger {
    constructor() {
        this.logs = [];
        this.maxLogs = 100;
    }

    log(level, message) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = {
            timestamp,
            level,
            message,
            id: Date.now() + Math.random()
        };
        
        this.logs.push(logEntry);
        
        // Ограничиваем количество логов
        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }
        
        // Выводим в консоль
        console.log(`[${timestamp}] ${level}: ${message}`);
        
        // Обновляем UI
        this.updateUI();
    }

    info(message) {
        this.log('INFO', message);
    }

    error(message) {
        this.log('ERROR', message);
    }

    warn(message) {
        this.log('WARN', message);
    }

    updateUI() {
        const logPanel = document.getElementById('logPanel');
        const logEntries = document.getElementById('logEntries');
        
        if (logPanel && logEntries) {
            logPanel.style.display = 'block';
            logEntries.innerHTML = this.logs.map(log => 
                `<div class="log-entry ${log.level.toLowerCase()}">[${log.timestamp}] ${log.level}: ${log.message}</div>`
            ).join('');
            
            // Прокручиваем вниз
            logPanel.scrollTop = logPanel.scrollHeight;
        }
    }
}