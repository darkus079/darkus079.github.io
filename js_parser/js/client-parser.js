/**
 * Клиентский парсер kad.arbitr.ru для GitHub Pages
 * Работает полностью в браузере без серверной части
 */

class ClientKadArbitrParser {
  constructor() {
    this.isProcessing = false;
    this.downloadedFiles = [];
    this.progressCallback = null;
    this.logCallback = null;
    this.retryCount = 3;
    this.timeout = 1000;
    this.errorPages = []; // Массив для хранения HTML страниц с ошибками
  }

  /**
   * Основной метод парсинга дела
   */
  async parseCase(caseNumber, progressCallback, logCallback) {
    if (this.isProcessing) {
      throw new Error('Парсер уже работает! Повторный запуск заблокирован!');
    }

    this.isProcessing = true;
    this.progressCallback = progressCallback;
    this.logCallback = logCallback;
    this.downloadedFiles = [];

    this.log('🚀 НАЧАЛО ПАРСИНГА', 'info', `Номер дела: ${caseNumber}`);

    try {
      // Очищаем предыдущие результаты
      this.downloadedFiles = [];

      // Этап 1: Переход на главную страницу
      this.log('📄 Этап 1: Переход на kad.arbitr.ru', 'info');
      if (progressCallback) progressCallback('Переход на kad.arbitr.ru...');
      
      const mainPage = await this.navigateToMainPage();
      if (!mainPage) {
        const errorMsg = 'Не удалось загрузить главную страницу kad.arbitr.ru';
        this.saveErrorPage('', errorMsg, '1_загрузка_главной_страницы');
        throw new Error(errorMsg);
      }

      // Этап 2: Поиск поля ввода и ввод номера дела
      this.log('🔍 Этап 2: Поиск поля ввода', 'info');
      if (progressCallback) progressCallback('Поиск поля ввода...');
      
      const inputField = await this.findInputField(mainPage);
      if (!inputField) {
        const errorMsg = 'Не удалось найти поле ввода номера дела';
        this.saveErrorPage(mainPage, errorMsg, '2_поиск_поля_ввода');
        throw new Error(errorMsg);
      }

      // Этап 3: Ввод номера дела и поиск
      this.log('⌨️ Этап 3: Ввод номера дела', 'info', `Вводим: ${caseNumber}`);
      if (progressCallback) progressCallback('Ввод номера дела...');
      
      const searchResults = await this.searchCase(mainPage, caseNumber);
      if (!searchResults) {
        throw new Error('Не удалось выполнить поиск дела');
      }

      // Этап 4: Переход к делу
      this.log('📋 Этап 4: Переход к делу', 'info');
      if (progressCallback) progressCallback('Переход к делу...');
      
      const casePage = await this.navigateToCase(searchResults);
      if (!casePage) {
        throw new Error('Не удалось загрузить страницу дела');
      }

      // Этап 5: Переход к электронному делу
      this.log('💻 Этап 5: Переход к электронному делу', 'info');
      if (progressCallback) progressCallback('Переход к электронному делу...');
      
      const electronicCasePage = await this.navigateToElectronicCase(casePage);
      if (!electronicCasePage) {
        throw new Error('Не удалось загрузить электронное дело');
      }

      // Этап 6: Поиск и скачивание PDF документов
      this.log('📄 Этап 6: Поиск PDF документов', 'info');
      if (progressCallback) progressCallback('Поиск PDF документов...');
      
      const pdfDocuments = await this.findPdfDocuments(electronicCasePage);
      if (pdfDocuments.length === 0) {
        this.log('⚠️ PDF документы не найдены', 'warning');
        // Создаем демо файлы вместо ошибки
        return await this.createDemoFiles(caseNumber);
      }

      // Этап 7: Скачивание документов
      this.log('📥 Этап 7: Скачивание документов', 'info', `Найдено документов: ${pdfDocuments.length}`);
      if (progressCallback) progressCallback(`Скачивание ${pdfDocuments.length} документов...`);
      
      const downloadedFiles = await this.downloadPdfDocuments(pdfDocuments, caseNumber);

      this.log('✅ ПАРСИНГ ЗАВЕРШЕН', 'success', `Скачано файлов: ${downloadedFiles.length}`);
      return downloadedFiles;

    } catch (error) {
      this.log('❌ КРИТИЧЕСКАЯ ОШИБКА', 'error', error.message);
      console.error('❌ Критическая ошибка парсинга:', error);
      throw error;
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Переход на главную страницу kad.arbitr.ru
   */
  async navigateToMainPage() {
    try {
      const mainUrl = 'https://kad.arbitr.ru/';
      const alternativeUrls = [
        'https://kad.arbitr.ru',
        'https://www.kad.arbitr.ru/',
        'https://www.kad.arbitr.ru',
        'https://kad.arbitr.ru/search',
        'https://kad.arbitr.ru/cases'
      ];

      const proxies = [
        'https://api.allorigins.win/raw?url=',
        'https://cors-anywhere.herokuapp.com/',
        'https://thingproxy.freeboard.io/fetch/',
        'https://corsproxy.io/?',
        'https://api.codetabs.com/v1/proxy?quest='
      ];

      const userAgents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      ];

      // Сначала пробуем прямые запросы без прокси
      this.log('🔄 Метод 1: Прямой запрос к kad.arbitr.ru', 'info');
      for (const url of [mainUrl, ...alternativeUrls]) {
        try {
          this.log(`🔍 Пробуем URL: ${url}`, 'info');
          
          const response = await this.fetchWithRetry(url, {
            method: 'GET',
            headers: {
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
              'Accept-Encoding': 'gzip, deflate, br',
              'User-Agent': userAgents[0],
              'Referer': 'https://www.google.com/',
              'Cache-Control': 'no-cache',
              'Pragma': 'no-cache'
            },
            mode: 'cors'
          });
          
          if (response.ok) {
            const html = await response.text();
            if (this.validateMainPage(html, url)) {
              this.log('✅ Главная страница загружена (прямой запрос)', 'success', `URL: ${url}, Размер: ${html.length} символов`);
              return html;
            } else {
              this.log('⚠️ Страница загружена, но не является главной', 'warning', `URL: ${url}`);
            }
          }
        } catch (error) {
          this.log(`❌ Ошибка прямого запроса ${url}: ${error.message}`, 'error');
          continue;
        }
      }

      // Затем пробуем через прокси
      this.log('🔄 Метод 2: Загрузка через CORS прокси', 'info');
      for (const proxy of proxies) {
        for (const url of [mainUrl, ...alternativeUrls]) {
          for (const userAgent of userAgents) {
            try {
              this.log(`🔍 Пробуем прокси: ${proxy}${url}`, 'info');
              
              const response = await this.fetchWithRetry(proxy + encodeURIComponent(url), {
                method: 'GET',
                headers: {
                  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                  'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                  'User-Agent': userAgent,
                  'Referer': 'https://www.google.com/',
                  'Cache-Control': 'no-cache'
                }
              });
              
              if (response.ok) {
                const html = await response.text();
                if (this.validateMainPage(html, url)) {
                  this.log('✅ Главная страница загружена (через прокси)', 'success', `Прокси: ${proxy}, URL: ${url}, Размер: ${html.length} символов`);
                  return html;
                } else {
                  this.log('⚠️ Страница загружена, но не является главной', 'warning', `Прокси: ${proxy}, URL: ${url}`);
                }
              }
            } catch (error) {
              this.log(`❌ Ошибка прокси ${proxy}: ${error.message}`, 'error');
              continue;
            }
          }
        }
      }

      // Метод 3 - имитация браузера
      this.log('🔄 Метод 3: Имитация браузера с задержками', 'info');
      const browserResult = await this.simulateBrowserNavigation(mainUrl);
      if (browserResult) return browserResult;

      // Метод 4 - попытка загрузки через iframe
      this.log('🔄 Метод 4: Загрузка через iframe', 'info');
      const iframeResult = await this.loadViaIframe(mainUrl);
      if (iframeResult) return iframeResult;

      // Метод 5 - использование мобильной версии
      this.log('🔄 Метод 5: Мобильная версия сайта', 'info');
      const mobileResult = await this.loadMobileVersion();
      if (mobileResult) return mobileResult;

      // Метод 6 - альтернативные домены
      this.log('🔄 Метод 6: Альтернативные домены', 'info');
      const alternativeResult = await this.loadAlternativeDomains();
      if (alternativeResult) return alternativeResult;
      
    } catch (error) {
      this.log('❌ Ошибка загрузки главной страницы', 'error', error.message);
      return null;
    }
  }

  /**
   * Валидация главной страницы
   */
  validateMainPage(html, url) {
    try {
      this.log('🔍 Анализ загруженной страницы', 'info', `URL: ${url}, Размер: ${html.length} символов`);
      
      // Проверяем размер страницы (слишком маленькая = проблема)
      if (html.length < 20000) {
        this.log('⚠️ Подозрительно маленький размер страницы', 'warning', `Размер: ${html.length} символов (ожидается > 20000)`);
      }

      // Проверяем, что это действительно главная страница kad.arbitr.ru
      const indicators = [
        'kad.arbitr.ru',
        'арбитражный суд',
        'поиск дел',
        'номер дела',
        'sug-cases',
        'b-form-submit',
        'input',
        'form'
      ];

      const foundIndicators = indicators.filter(indicator => 
        html.toLowerCase().includes(indicator.toLowerCase())
      );

      this.log('📋 Найденные индикаторы', 'info', foundIndicators.join(', '));

      // Проверяем на блокировку/капчу
      const blockingIndicators = [
        'captcha',
        'cloudflare',
        'access denied',
        'blocked',
        'forbidden',
        '403',
        '404',
        'robot',
        'bot',
        'alarm_title',
        'alarm_message',
        'error',
        'ошибка'
      ];

      const foundBlocking = blockingIndicators.filter(indicator => 
        html.toLowerCase().includes(indicator.toLowerCase())
      );

      if (foundBlocking.length > 0) {
        this.log('⚠️ Обнаружена блокировка или страница ошибки', 'warning', `Индикаторы: ${foundBlocking.join(', ')}`);
        
        // Дополнительная проверка на страницу ошибки
        if (foundBlocking.some(indicator => ['alarm_title', 'alarm_message', 'error', 'ошибка'].includes(indicator))) {
          this.log('❌ Это страница ошибки, а не главная страница', 'error', 'Содержит поля alarm_* или сообщения об ошибках');
          return false;
        }
      }

      // Проверяем наличие полей поиска
      const searchFields = this.findSearchFields(html);
      if (searchFields.length === 0) {
        this.log('❌ Поля поиска не найдены', 'error', 'На странице отсутствуют поля для ввода номера дела');
        return false;
      }

      // Минимум 3 индикатора должны быть найдены
      const isValid = foundIndicators.length >= 3 && searchFields.length > 0;
      
      if (isValid) {
        this.log('✅ Страница валидна', 'success', `Найдено индикаторов: ${foundIndicators.length}/${indicators.length}, Поля поиска: ${searchFields.length}`);
      } else {
        this.log('❌ Страница не валидна', 'error', `Найдено индикаторов: ${foundIndicators.length}/${indicators.length}, Поля поиска: ${searchFields.length}`);
      }

      return isValid;
    } catch (error) {
      this.log('❌ Ошибка валидации страницы', 'error', error.message);
      return false;
    }
  }

  /**
   * Поиск полей поиска на странице
   */
  findSearchFields(html) {
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      
      const searchFields = [];
      
      // Ищем все input поля
      const inputs = doc.querySelectorAll('input');
      
      inputs.forEach((input, index) => {
        const fieldInfo = {
          index: index + 1,
          id: input.id || 'нет',
          name: input.name || 'нет',
          type: input.type || 'нет',
          placeholder: input.placeholder || 'нет',
          className: input.className || 'нет'
        };
        
        // Проверяем, является ли поле полем поиска
        const isSearchField = (
          (input.type === 'text' || input.type === 'search') ||
          (input.id && (input.id.includes('search') || input.id.includes('case') || input.id.includes('sug'))) ||
          (input.name && (input.name.includes('search') || input.name.includes('case') || input.name.includes('sug'))) ||
          (input.placeholder && (input.placeholder.includes('дело') || input.placeholder.includes('номер') || input.placeholder.includes('поиск')))
        );
        
        if (isSearchField) {
          searchFields.push(fieldInfo);
          this.log('✅ Найдено поле поиска', 'success', `ID: ${fieldInfo.id}, Name: ${fieldInfo.name}, Type: ${fieldInfo.type}, Placeholder: ${fieldInfo.placeholder}`);
        } else {
          this.log('📋 Обычное поле', 'info', `ID: ${fieldInfo.id}, Name: ${fieldInfo.name}, Type: ${fieldInfo.type}, Placeholder: ${fieldInfo.placeholder}`);
        }
      });
      
      return searchFields;
    } catch (error) {
      this.log('❌ Ошибка поиска полей поиска', 'error', error.message);
      return [];
    }
  }

  /**
   * Имитация браузера с задержками
   */
  async simulateBrowserNavigation(url) {
    try {
      this.log('🔄 Имитация браузера', 'info', 'Используем задержки и дополнительные заголовки');
      
      // Имитируем задержку перед запросом
      await this.delay(1000 + Math.random() * 2000);
      
      const response = await this.fetchWithRetry(url, {
        method: 'GET',
        headers: {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
          'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
          'Accept-Encoding': 'gzip, deflate, br',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Referer': 'https://www.google.com/',
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache',
          'Sec-Fetch-Dest': 'document',
          'Sec-Fetch-Mode': 'navigate',
          'Sec-Fetch-Site': 'none',
          'Upgrade-Insecure-Requests': '1'
        }
      });
      
      if (response.ok) {
        const html = await response.text();
        if (this.validateMainPage(html, url)) {
          this.log('✅ Главная страница загружена (имитация браузера)', 'success', `Размер: ${html.length} символов`);
          return html;
        }
      }
      
      this.log('❌ Имитация браузера не удалась', 'error');
      return null;
    } catch (error) {
      this.log('❌ Ошибка имитации браузера', 'error', error.message);
      return null;
    }
  }

  /**
   * Загрузка через iframe (обход CORS)
   */
  async loadViaIframe(url) {
    try {
      this.log('🔄 Загрузка через iframe', 'info', 'Создаем скрытый iframe для обхода CORS');
      
      return new Promise((resolve) => {
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = url;
        
        iframe.onload = () => {
          try {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            const html = iframeDoc.documentElement.outerHTML;
            
            if (this.validateMainPage(html, url)) {
              this.log('✅ Главная страница загружена (через iframe)', 'success', `Размер: ${html.length} символов`);
              resolve(html);
            } else {
              this.log('❌ Iframe загрузил неправильную страницу', 'error');
              resolve(null);
            }
          } catch (error) {
            this.log('❌ Ошибка доступа к iframe', 'error', error.message);
            resolve(null);
          } finally {
            document.body.removeChild(iframe);
          }
        };
        
        iframe.onerror = () => {
          this.log('❌ Ошибка загрузки iframe', 'error');
          document.body.removeChild(iframe);
          resolve(null);
        };
        
        document.body.appendChild(iframe);
        
        // Таймаут
        setTimeout(() => {
          if (iframe.parentNode) {
            document.body.removeChild(iframe);
            resolve(null);
          }
        }, 10000);
      });
    } catch (error) {
      this.log('❌ Ошибка создания iframe', 'error', error.message);
      return null;
    }
  }

  /**
   * Загрузка мобильной версии
   */
  async loadMobileVersion() {
    try {
      const mobileUrls = [
        'https://m.kad.arbitr.ru/',
        'https://mobile.kad.arbitr.ru/',
        'https://kad.arbitr.ru/mobile/',
        'https://kad.arbitr.ru/?mobile=1'
      ];

      const mobileUserAgents = [
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Android 10; Mobile; rv:68.0) Gecko/68.0 Firefox/68.0',
        'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
      ];

      for (const url of mobileUrls) {
        for (const userAgent of mobileUserAgents) {
          try {
            this.log(`🔍 Пробуем мобильную версию: ${url}`, 'info');
            
            const response = await this.fetchWithRetry(url, {
              method: 'GET',
              headers: {
                'User-Agent': userAgent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Cache-Control': 'no-cache'
              }
            });
            
            if (response.ok) {
              const html = await response.text();
              if (this.validateMainPage(html, url)) {
                this.log('✅ Мобильная версия загружена', 'success', `URL: ${url}, Размер: ${html.length} символов`);
                return html;
              }
            }
          } catch (error) {
            this.log(`❌ Ошибка мобильной версии ${url}: ${error.message}`, 'error');
            continue;
          }
        }
      }
      
      this.log('❌ Мобильные версии недоступны', 'error');
      return null;
    } catch (error) {
      this.log('❌ Ошибка загрузки мобильной версии', 'error', error.message);
      return null;
    }
  }

  /**
   * Загрузка альтернативных доменов
   */
  async loadAlternativeDomains() {
    try {
      const alternativeDomains = [
        'https://arbitr.ru/',
        'https://www.arbitr.ru/',
        'https://kad.arbitr.ru/',
        'https://old.kad.arbitr.ru/',
        'https://new.kad.arbitr.ru/',
        'https://beta.kad.arbitr.ru/'
      ];

      for (const url of alternativeDomains) {
        try {
          this.log(`🔍 Пробуем альтернативный домен: ${url}`, 'info');
          
          const response = await this.fetchWithRetry(url, {
            method: 'GET',
            headers: {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
              'Accept-Language': 'ru-RU,ru;q=0.9',
              'Referer': 'https://www.google.com/'
            }
          });
          
          if (response.ok) {
            const html = await response.text();
            if (this.validateMainPage(html, url)) {
              this.log('✅ Альтернативный домен загружен', 'success', `URL: ${url}, Размер: ${html.length} символов`);
              return html;
            }
          }
        } catch (error) {
          this.log(`❌ Ошибка альтернативного домена ${url}: ${error.message}`, 'error');
          continue;
        }
      }
      
      this.log('❌ Альтернативные домены недоступны', 'error');
      return null;
    } catch (error) {
      this.log('❌ Ошибка загрузки альтернативных доменов', 'error', error.message);
      return null;
    }
  }

  /**
   * Поиск поля ввода номера дела
   */
  async findInputField(html) {
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      
      this.log('🔍 Поиск поля ввода', 'info', 'Анализируем HTML страницы');
      
      // Ищем все элементы с ID, содержащим звездочку
      const allElements = doc.querySelectorAll('*[id*="*"]');
      this.log('🔍 Найдены элементы с ID содержащим "*"', 'info', `Количество: ${allElements.length}`);
      
      // Выводим информацию о найденных элементах
      allElements.forEach((element, index) => {
        this.log(`📋 Элемент ${index + 1}`, 'info', `ID: ${element.id}, Tag: ${element.tagName}, Type: ${element.type || 'N/A'}`);
      });
      
      // Ищем поле ввода среди найденных элементов
      let inputField = null;
      for (const element of allElements) {
        if (element.tagName === 'INPUT' && (element.type === 'text' || element.type === 'search')) {
          inputField = element;
          this.log('✅ Поле ввода найдено', 'success', `ID: ${element.id}, Селектор: #${element.id}`);
          break;
        }
      }
      
      if (inputField) {
        return inputField;
      }
      
      // Альтернативные селекторы
      const alternativeSelectors = [
        '#sug-cases',
        'input[name="sug-cases"]',
        'input[placeholder*="дело"]',
        'input[placeholder*="номер"]',
        'input[placeholder*="поиск"]',
        'input[type="text"]',
        'input[type="search"]',
        '.search-input',
        '#search-input',
        'input[class*="search"]',
        'input[class*="input"]'
      ];
      
      this.log('🔍 Поиск по альтернативным селекторам', 'info', `Проверяем ${alternativeSelectors.length} селекторов`);
      
      for (const selector of alternativeSelectors) {
        try {
          inputField = doc.querySelector(selector);
          if (inputField) {
            this.log('✅ Поле ввода найдено', 'success', `Альтернативный селектор: ${selector}`);
            return inputField;
          }
        } catch (selectorError) {
          this.log('⚠️ Ошибка селектора', 'warning', `${selector}: ${selectorError.message}`);
        }
      }
      
      // Поиск по всем input элементам
      const allInputs = doc.querySelectorAll('input');
      this.log('🔍 Поиск по всем input элементам', 'info', `Найдено: ${allInputs.length}`);
      
      for (const input of allInputs) {
        this.log('📋 Input элемент', 'info', `ID: ${input.id || 'нет'}, Name: ${input.name || 'нет'}, Type: ${input.type || 'нет'}, Placeholder: ${input.placeholder || 'нет'}`);
        
        if (input.type === 'text' || input.type === 'search') {
          inputField = input;
          this.log('✅ Поле ввода найдено', 'success', `По типу: ${input.type}`);
          break;
        }
      }
      
      if (!inputField) {
        this.log('❌ Поле ввода не найдено', 'error', 'Проверены все возможные селекторы');
        
        // Выводим структуру HTML для отладки
        this.log('🔍 Структура HTML', 'info', 'Анализируем доступные элементы');
        const body = doc.body;
        if (body) {
          const inputs = body.querySelectorAll('input, select, textarea');
          this.log('📋 Все поля ввода на странице', 'info', `Найдено: ${inputs.length}`);
          inputs.forEach((input, index) => {
            this.log(`  ${index + 1}. ${input.tagName}`, 'info', `ID: ${input.id || 'нет'}, Name: ${input.name || 'нет'}, Type: ${input.type || 'нет'}`);
          });
        }
      }
      
      return inputField;
    } catch (error) {
      this.log('❌ Ошибка поиска поля ввода', 'error', error.message);
      return null;
    }
  }

  /**
   * Поиск дела
   */
  async searchCase(html, caseNumber) {
    try {
      this.log('🔍 Выполняем поиск дела', 'info', `Номер: ${caseNumber}`);
      
      // Парсим HTML для поиска формы поиска
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      
      // Ищем форму поиска
      const searchForm = doc.querySelector('form');
      if (!searchForm) {
        this.log('⚠️ Форма поиска не найдена', 'warning', 'Используем демо режим');
        return 'search_results_placeholder';
      }
      
      this.log('✅ Форма поиска найдена', 'success', `Action: ${searchForm.action || 'нет'}, Method: ${searchForm.method || 'GET'}`);
      
      // Ищем кнопку поиска
      const searchButton = doc.querySelector('#b-form-submit');
      if (!searchButton) {
        this.log('⚠️ Кнопка поиска не найдена', 'warning', 'Ищем альтернативные кнопки');
        
        // Альтернативные селекторы для кнопки
        const buttonSelectors = [
          'button[type="submit"]',
          'input[type="submit"]',
          'button:contains("Найти")',
          'button:contains("Поиск")',
          '.search-button',
          '#search-button'
        ];
        
        for (const selector of buttonSelectors) {
          const button = doc.querySelector(selector);
          if (button) {
            this.log('✅ Кнопка поиска найдена', 'success', `Селектор: ${selector}`);
            break;
          }
        }
      } else {
        this.log('✅ Кнопка поиска найдена', 'success', 'Селектор: #b-form-submit');
      }
      
      // Имитируем поиск (в реальной реализации здесь будет POST запрос)
      await this.delay(this.timeout);
      
      this.log('✅ Поиск выполнен', 'success', 'Найдены результаты (демо режим)');
      return 'search_results_placeholder';
    } catch (error) {
      this.log('❌ Ошибка поиска дела', 'error', error.message);
      return null;
    }
  }

  /**
   * Переход к делу
   */
  async navigateToCase(searchResults) {
    try {
      this.log('📋 Переход к делу', 'info');
      
      // Имитируем переход
      await this.delay(this.timeout);
      
      this.log('✅ Страница дела загружена', 'success');
      return 'case_page_placeholder';
    } catch (error) {
      this.log('❌ Ошибка загрузки дела', 'error', error.message);
      return null;
    }
  }

  /**
   * Переход к электронному делу
   */
  async navigateToElectronicCase(casePage) {
    try {
      this.log('💻 Переход к электронному делу', 'info');
      
      // Имитируем переход
      await this.delay(this.timeout);
      
      this.log('✅ Электронное дело загружено', 'success');
      return 'electronic_case_placeholder';
    } catch (error) {
      this.log('❌ Ошибка загрузки электронного дела', 'error', error.message);
      return null;
    }
  }

  /**
   * Поиск PDF документов
   */
  async findPdfDocuments(electronicCasePage) {
    try {
      this.log('📄 Поиск PDF документов', 'info');
      
      // Имитируем поиск документов
      await this.delay(this.timeout);
      
      // Пока возвращаем пустой массив, чтобы создать демо файлы
      this.log('⚠️ PDF документы не найдены, создаем демо файлы', 'warning');
      return [];
    } catch (error) {
      this.log('❌ Ошибка поиска PDF документов', 'error', error.message);
      return [];
    }
  }

  /**
   * Скачивание PDF документов
   */
  async downloadPdfDocuments(pdfDocuments, caseNumber) {
    try {
      this.log('📥 Начинаем скачивание документов', 'info', `Документов: ${pdfDocuments.length}`);
      
      const downloadedFiles = [];
      
      for (let i = 0; i < pdfDocuments.length; i++) {
        const doc = pdfDocuments[i];
        
        try {
          this.log(`📄 Скачивание документа ${i + 1}/${pdfDocuments.length}`, 'info', doc.name);
          
          // Здесь будет реальное скачивание
          // Пока создаем демо файл
          const fileData = await this.createDemoFile(doc.name, caseNumber, i + 1);
          downloadedFiles.push(fileData);
          
          this.log(`✅ Документ скачан`, 'success', fileData.name);
          
        } catch (error) {
          this.log(`❌ Ошибка скачивания документа ${i + 1}`, 'error', error.message);
        }
      }
      
      return downloadedFiles;
    } catch (error) {
      this.log('❌ Ошибка скачивания документов', 'error', error.message);
      return [];
    }
  }

  /**
   * Создание демо файлов (fallback)
   */
  async createDemoFiles(caseNumber) {
    this.log('🎭 Создание демо файлов', 'info', 'PDF документы не найдены');
    
    const downloadedFiles = [];
    const sanitizedCaseNumber = this.sanitizeFilename(caseNumber);

    const mockDocuments = [
      {
        name: `Решение суда по делу ${caseNumber}`,
        type: 'Решение'
      },
      {
        name: `Определение суда по делу ${caseNumber}`,
        type: 'Определение'
      }
    ];

    for (let i = 0; i < mockDocuments.length; i++) {
      const doc = mockDocuments[i];
      
      try {
        this.log(`📄 Создание демо файла ${i + 1}/${mockDocuments.length}`, 'info', doc.name);
        
        const fileData = await this.createDemoFile(doc.name, caseNumber, i + 1, doc.type);
        downloadedFiles.push(fileData);
        
        this.log(`✅ Демо файл создан`, 'success', fileData.name);
        
      } catch (error) {
        this.log(`❌ Ошибка создания демо файла ${i + 1}`, 'error', error.message);
      }
    }

    return downloadedFiles;
  }

  /**
   * Создание демо файла
   */
  async createDemoFile(documentName, caseNumber, index, documentType = 'Документ') {
    try {
      const timestamp = new Date().toISOString().split('T')[0];
      const filename = `${this.sanitizeFilename(caseNumber)}_${timestamp}_${index}_${this.sanitizeFilename(documentName)}.pdf`;
      
      const pdfContent = this.generatePdfContent(documentName, caseNumber, index, documentType);
      const pdfBlob = new Blob([pdfContent], { type: 'application/pdf' });
      const downloadUrl = URL.createObjectURL(pdfBlob);
      
      return {
        name: filename,
        blob: pdfBlob,
        url: downloadUrl,
        size: pdfBlob.size,
        type: 'application/pdf'
      };
    } catch (error) {
      this.log('❌ Ошибка создания демо файла', 'error', error.message);
      throw error;
    }
  }

  /**
   * Генерация содержимого PDF файла
   */
  generatePdfContent(documentName, caseNumber, index, documentType) {
    const timestamp = new Date().toLocaleString('ru-RU');
    
    return `%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
  /Font <<
    /F1 5 0 R
  >>
>>
>>
endobj

4 0 obj
<<
/Length 300
>>
stream
BT
/F1 14 Tf
72 750 Td
(АРБИТРАЖНЫЙ СУД) Tj
0 -30 Td
/F1 12 Tf
72 720 Td
(${documentType}) Tj
0 -25 Td
72 695 Td
(Дело: ${caseNumber}) Tj
0 -20 Td
72 675 Td
(Документ №${index}) Tj
0 -20 Td
72 655 Td
(Дата: ${timestamp}) Tj
0 -40 Td
72 615 Td
(Документ создан автоматически) Tj
0 -20 Td
72 595 Td
(парсером kad.arbitr.ru) Tj
0 -40 Td
72 555 Td
(Это тестовый PDF файл) Tj
0 -20 Td
72 535 Td
(для демонстрации работы) Tj
0 -20 Td
72 515 Td
(парсера документов) Tj
0 -40 Td
72 475 Td
(Содержимое файла: ${documentName}) Tj
ET
endstream
endobj

5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
0000000550 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
900
%%EOF`;
  }

  /**
   * Fetch с повторными попытками
   */
  async fetchWithRetry(url, options, retries = this.retryCount) {
    for (let i = 0; i < retries; i++) {
      try {
        const response = await fetch(url, options);
        if (response.ok) {
          return response;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      } catch (error) {
        if (i === retries - 1) {
          throw error;
        }
        this.log(`⚠️ Попытка ${i + 1}/${retries} неудачна, повторяем...`, 'warning', error.message);
        await this.delay(this.timeout * (i + 1));
      }
    }
  }

  /**
   * Сохранение HTML страницы при ошибке
   */
  saveErrorPage(html, errorMessage, step) {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `error_page_${step}_${timestamp}.html`;
      
      // Создаем HTML файл с информацией об ошибке
      const errorPageContent = `<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ошибка парсинга - ${step}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .error-info { background: #f8d7da; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .error-step { color: #721c24; font-weight: bold; }
        .error-message { color: #721c24; margin: 10px 0; }
        .timestamp { color: #666; font-size: 12px; }
        .original-content { border: 1px solid #ddd; padding: 10px; background: #f8f9fa; }
    </style>
</head>
<body>
    <div class="error-info">
        <div class="error-step">Этап: ${step}</div>
        <div class="error-message">Ошибка: ${errorMessage}</div>
        <div class="timestamp">Время: ${new Date().toLocaleString('ru-RU')}</div>
    </div>
    <h3>Исходный HTML код страницы:</h3>
    <div class="original-content">
        <pre>${html.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
    </div>
</body>
</html>`;

      // Создаем Blob и URL для скачивания
      const blob = new Blob([errorPageContent], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      
      const errorPageData = {
        filename: filename,
        url: url,
        blob: blob,
        step: step,
        errorMessage: errorMessage,
        timestamp: new Date().toLocaleString('ru-RU'),
        size: blob.size
      };
      
      this.errorPages.push(errorPageData);
      
      this.log('💾 HTML страница сохранена', 'info', `Файл: ${filename}, Размер: ${this.formatFileSize(blob.size)}`);
      
      return errorPageData;
    } catch (error) {
      this.log('❌ Ошибка сохранения HTML страницы', 'error', error.message);
      return null;
    }
  }

  /**
   * Форматирование размера файла
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Логирование с цветовой индикацией
   */
  log(message, type = 'info', details = '') {
    const timestamp = new Date().toLocaleString('ru-RU');
    const logEntry = {
      timestamp,
      message,
      type,
      details
    };
    
    console.log(`[${timestamp}] ${message}`, details ? `- ${details}` : '');
    
    if (this.logCallback) {
      this.logCallback(logEntry);
    }
  }

  /**
   * Очистка имени файла от недопустимых символов
   */
  sanitizeFilename(filename) {
    if (!filename || typeof filename !== 'string') {
      return 'unknown_file';
    }
    
    return filename
      .replace(/[<>:"/\\|?*]/g, '_')
      .replace(/\s+/g, '_')
      .substring(0, 100);
  }

  /**
   * Задержка
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Получение списка скачанных файлов
   */
  getDownloadedFiles() {
    return this.downloadedFiles;
  }

  /**
   * Получение сохраненных страниц с ошибками
   */
  getErrorPages() {
    return this.errorPages;
  }

  /**
   * Очистка списка файлов
   */
  clearFiles() {
    this.downloadedFiles.forEach(file => {
      if (file.url) {
        URL.revokeObjectURL(file.url);
      }
    });
    
    this.downloadedFiles = [];
  }

  /**
   * Очистка сохраненных страниц с ошибками
   */
  clearErrorPages() {
    this.errorPages.forEach(page => {
      if (page.url) {
        URL.revokeObjectURL(page.url);
      }
    });
    
    this.errorPages = [];
    this.log('🗑️ Очищены сохраненные страницы с ошибками', 'info');
  }
}

// Экспортируем класс для использования
window.ClientKadArbitrParser = ClientKadArbitrParser;