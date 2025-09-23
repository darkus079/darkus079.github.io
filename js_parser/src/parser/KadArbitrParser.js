const puppeteer = require('puppeteer');
const fs = require('fs-extra');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

class KadArbitrParser {
  constructor() {
    this.browser = null;
    this.page = null;
    this.filesDir = path.join(__dirname, '../../files');
    this.downloadsDir = this.getDownloadsDirectory();
    this.isProcessing = false;
    
    // Создаем папку files если её нет
    fs.ensureDirSync(this.filesDir);
    
    console.log(`📁 Папка для скачивания: ${this.downloadsDir}`);
    console.log(`📁 Папка для сохранения: ${path.resolve(this.filesDir)}`);
  }
  
  getDownloadsDirectory() {
    try {
      const homeDir = require('os').homedir();
      const downloadsPath = path.join(homeDir, 'Downloads');
      
      if (fs.existsSync(downloadsPath)) {
        return downloadsPath;
      }
      
      // Альтернативный путь для Windows
      const windowsDownloads = path.join(homeDir, 'Загрузки');
      if (fs.existsSync(windowsDownloads)) {
        return windowsDownloads;
      }
      
      console.warn('⚠️ Папка Загрузки не найдена, используем текущую папку');
      return process.cwd();
      
    } catch (error) {
      console.warn('⚠️ Ошибка получения пути к Загрузкам:', error);
      return process.cwd();
    }
  }
  
  async initBrowser() {
    try {
      console.log('🌐 Инициализация браузера...');
      
      this.browser = await puppeteer.launch({
        headless: 'new',
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
        ],
        defaultViewport: {
          width: 1920,
          height: 1080
        }
      });
      
      this.page = await this.browser.newPage();
      
      // Настройка User-Agent и других параметров
      await this.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
      
      // Настройка скачивания файлов
      await this.page._client.send('Page.setDownloadBehavior', {
        behavior: 'allow',
        downloadPath: this.downloadsDir
      });
      
      // Маскировка автоматизации
      await this.page.evaluateOnNewDocument(() => {
        Object.defineProperty(navigator, 'webdriver', {
          get: () => undefined,
        });
        
        // Удаляем следы автоматизации
        delete navigator.__proto__.webdriver;
        
        // Маскируем Chrome runtime
        window.chrome = {
          runtime: {},
          loadTimes: function() {},
          csi: function() {},
          app: {}
        };
        
        // Добавляем реалистичные свойства
        Object.defineProperty(navigator, 'languages', {
          get: () => ['ru-RU', 'ru', 'en-US', 'en']
        });
      });
      
      console.log('✅ Браузер инициализирован');
      return true;
      
    } catch (error) {
      console.error('❌ Ошибка инициализации браузера:', error);
      return false;
    }
  }
  
  async closeBrowser() {
    try {
      if (this.browser) {
        await this.browser.close();
        this.browser = null;
        this.page = null;
        console.log('✅ Браузер закрыт');
      }
    } catch (error) {
      console.error('❌ Ошибка закрытия браузера:', error);
    }
  }
  
  async humanDelay(min, max, description = '') {
    const delay = Math.floor(Math.random() * (max - min + 1)) + min;
    console.log(`⏳ ${description} (${delay}с)`);
    await new Promise(resolve => setTimeout(resolve, delay * 1000));
  }
  
  async simulateHumanBehavior() {
    // Случайные движения мыши
    const viewport = this.page.viewport();
    const x = Math.random() * viewport.width;
    const y = Math.random() * viewport.height;
    
    await this.page.mouse.move(x, y, { steps: 10 });
    await this.humanDelay(0.5, 1.5);
  }
  
  async searchCase(caseNumber, progressCallback) {
    try {
      console.log(`🎯 Поиск дела: ${caseNumber}`);
      
      if (progressCallback) progressCallback('Переход на сайт kad.arbitr.ru...');
      
      // Переходим на сайт
      await this.page.goto('https://kad.arbitr.ru/', { 
        waitUntil: 'networkidle2',
        timeout: 30000 
      });
      
      await this.humanDelay(2, 4, 'ожидание загрузки главной страницы');
      
      if (progressCallback) progressCallback('Поиск поля ввода...');
      
      // Ищем поле поиска
      await this.page.waitForSelector('input[type="text"]', { timeout: 10000 });
      
      // Очищаем поле и вводим номер дела
      await this.page.click('input[type="text"]');
      await this.page.keyboard.down('Control');
      await this.page.keyboard.press('KeyA');
      await this.page.keyboard.up('Control');
      await this.page.type('input[type="text"]', caseNumber);
      
      await this.humanDelay(1, 2, 'ввод номера дела');
      
      if (progressCallback) progressCallback('Выполнение поиска...');
      
      // Нажимаем кнопку поиска
      await this.page.click('button[type="submit"]');
      
      // Ждем результатов поиска
      await this.page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 });
      
      if (progressCallback) progressCallback('Анализ результатов поиска...');
      
      // Ищем ссылки на дела
      const caseLinks = await this.page.evaluate(() => {
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
      
      console.log(`✅ Найдено дел: ${caseLinks.length}`);
      return caseLinks;
      
    } catch (error) {
      console.error('❌ Ошибка поиска дела:', error);
      throw error;
    }
  }
  
  async downloadPdfFiles(caseUrl, caseNumber, progressCallback) {
    try {
      console.log(`📁 Переход к делу: ${caseUrl}`);
      
      if (progressCallback) progressCallback('Переход к делу...');
      
      await this.page.goto(caseUrl, { 
        waitUntil: 'networkidle2',
        timeout: 30000 
      });
      
      await this.humanDelay(2, 3, 'ожидание загрузки страницы дела');
      
      if (progressCallback) progressCallback('Поиск вкладки "Электронное дело"...');
      
      // Ищем вкладку "Электронное дело"
      try {
        await this.page.waitForSelector('div.b-case-chrono-button-text', { timeout: 10000 });
        
        // Ищем кнопку с текстом "Электронное дело"
        const electronicTab = await this.page.evaluateHandle(() => {
          const buttons = Array.from(document.querySelectorAll('div.b-case-chrono-button-text'));
          return buttons.find(btn => btn.textContent.includes('Электронное дело'));
        });
        
        if (electronicTab) {
          await electronicTab.click();
          console.log('✅ Переход на вкладку "Электронное дело"');
        } else {
          throw new Error('Вкладка "Электронное дело" не найдена');
        }
        
      } catch (error) {
        console.warn('❌ Вкладка "Электронное дело" не найдена:', error);
        throw new Error('Вкладка "Электронное дело" недоступна');
      }
      
      await this.humanDelay(2, 3, 'ожидание загрузки списка документов');
      
      if (progressCallback) progressCallback('Поиск PDF документов...');
      
      // Ищем PDF ссылки
      const pdfLinks = await this.page.evaluate(() => {
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
      
      console.log(`📄 Найдено PDF документов: ${pdfLinks.length}`);
      
      if (progressCallback) progressCallback(`Скачивание ${pdfLinks.length} документов...`);
      
      const downloadedFiles = [];
      
      // Скачиваем каждый PDF файл
      for (let i = 0; i < pdfLinks.length; i++) {
        const link = pdfLinks[i];
        
        try {
          if (progressCallback) {
            progressCallback(`Скачивание документа ${i + 1} из ${pdfLinks.length}...`);
          }
          
          console.log(`📥 Скачивание: ${link.text}`);
          
          // Создаем уникальное имя файла
          const timestamp = new Date().toISOString().split('T')[0];
          const filename = `${caseNumber}_${timestamp}_${i + 1}_${this.sanitizeFilename(link.text)}.pdf`;
          const filePath = path.join(this.filesDir, filename);
          
          // Скачиваем файл
          const response = await this.page.goto(link.url, { 
            waitUntil: 'networkidle2',
            timeout: 30000 
          });
          
          if (response && response.ok()) {
            const buffer = await response.buffer();
            await fs.writeFile(filePath, buffer);
            downloadedFiles.push(filename);
            console.log(`✅ Скачан: ${filename}`);
          } else {
            console.warn(`❌ Ошибка скачивания: ${link.text}`);
          }
          
          await this.humanDelay(1, 2, 'пауза между скачиваниями');
          
        } catch (error) {
          console.error(`❌ Ошибка скачивания файла ${link.text}:`, error);
        }
      }
      
      console.log(`✅ Скачано файлов: ${downloadedFiles.length}`);
      return downloadedFiles;
      
    } catch (error) {
      console.error('❌ Ошибка скачивания PDF файлов:', error);
      throw error;
    }
  }
  
  sanitizeFilename(filename) {
    return filename
      .replace(/[<>:"/\\|?*]/g, '_')
      .replace(/\s+/g, '_')
      .substring(0, 100);
  }
  
  async parseCase(caseNumber, progressCallback) {
    if (this.isProcessing) {
      throw new Error('Парсер уже работает! Повторный запуск заблокирован!');
    }
    
    this.isProcessing = true;
    console.log(`🚀 НАЧАЛО ПАРСИНГА: ${caseNumber}`);
    
    try {
      // Очищаем папку files
      await fs.emptyDir(this.filesDir);
      
      // Инициализируем браузер
      if (progressCallback) progressCallback('Инициализация браузера...');
      if (!await this.initBrowser()) {
        throw new Error('Не удалось инициализировать браузер');
      }
      
      // Ищем дело
      if (progressCallback) progressCallback('Поиск дела...');
      const caseLinks = await this.searchCase(caseNumber, progressCallback);
      
      if (caseLinks.length === 0) {
        throw new Error('Дела не найдены');
      }
      
      // Скачиваем файлы из первого найденного дела
      const caseUrl = caseLinks[0].url;
      console.log(`🔄 Обработка дела: ${caseLinks[0].text}`);
      
      const downloadedFiles = await this.downloadPdfFiles(caseUrl, caseNumber, progressCallback);
      
      console.log(`✅ Обработка завершена. Скачано файлов: ${downloadedFiles.length}`);
      return downloadedFiles;
      
    } catch (error) {
      console.error('❌ Критическая ошибка парсинга:', error);
      throw error;
    } finally {
      // Закрываем браузер
      await this.closeBrowser();
      this.isProcessing = false;
    }
  }
  
  async getDownloadedFiles() {
    try {
      const files = await fs.readdir(this.filesDir);
      return files.filter(file => file.toLowerCase().endsWith('.pdf'));
    } catch (error) {
      console.error('❌ Ошибка получения списка файлов:', error);
      return [];
    }
  }
  
  async cleanupFilesDirectory() {
    try {
      await fs.emptyDir(this.filesDir);
      console.log('✅ Папка files очищена');
    } catch (error) {
      console.error('❌ Ошибка очистки папки files:', error);
    }
  }
}

module.exports = KadArbitrParser;
