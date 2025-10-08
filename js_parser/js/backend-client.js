/**
 * Клиент для работы с backend API парсера kad.arbitr.ru
 * Заменяет клиентский парсинг на вызовы к backend сервису
 */

class BackendClient {
  constructor() {
    this.baseUrl = '';
    this.isProcessing = false;
    this.downloadedFiles = [];
    this.progressCallback = null;
    this.logCallback = null;
    this.statusCheckInterval = null;
    this.currentCase = '';

    // Загружаем конфиг из публичного файла и сохраняем промис готовности
    this.configReady = this.loadConfig();
  }
  normalizeBaseUrl(url) {
    try {
      let u = (url || '').trim();
      if (!/^https?:\/\//i.test(u)) {
        u = `http://${u}`;
      }
      return u.replace(/\/$/, '');
    } catch (_) {
      return '';
    }
  }


  /**
   * Основной метод парсинга дела через backend
   */
  async parseCase(caseNumber, progressCallback, logCallback) {
    await this.ensureConfig();
    if (this.isProcessing) {
      throw new Error('Парсинг уже выполняется! Повторный запуск заблокирован!');
    }

    this.isProcessing = true;
    this.progressCallback = progressCallback;
    this.logCallback = logCallback;
    this.downloadedFiles = [];
    this.currentCase = caseNumber;

    this.log('🚀 НАЧАЛО ПАРСИНГА ЧЕРЕЗ BACKEND', 'info', `Номер дела: ${caseNumber}`);

    try {
      // Проверяем доступность backend
      await this.checkBackendHealth();

      // Отправляем запрос на парсинг
      this.log('📡 Отправка запроса на backend...', 'info');
      if (progressCallback) progressCallback('Отправка запроса на backend...');

      const response = await fetch(`${this.baseUrl}/api/parse`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          case_number: caseNumber
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const parseResponse = await response.json();
      this.log('✅ Запрос принят backend', 'success', parseResponse.message);

      // Запускаем мониторинг статуса
      this.startStatusMonitoring();

      // Ждем завершения парсинга
      const result = await this.waitForCompletion();

      this.log('✅ ПАРСИНГ ЗАВЕРШЕН', 'success', `Ссылки собраны`);
      // Получаем ссылки для дела
      const links = await this.getLinks(caseNumber);
      return links;

    } catch (error) {
      this.log('❌ КРИТИЧЕСКАЯ ОШИБКА', 'error', error.message);
      console.error('❌ Критическая ошибка парсинга:', error);
      throw error;
    } finally {
      this.isProcessing = false;
      this.stopStatusMonitoring();
    }
  }

  async loadConfig() {
    try {
      const resp = await fetch('/backend.config.json', { cache: 'no-store' });
      if (resp.ok) {
        const cfg = await resp.json();
        if (cfg && typeof cfg.backendBaseUrl === 'string' && cfg.backendBaseUrl.trim()) {
          this.baseUrl = this.normalizeBaseUrl(cfg.backendBaseUrl);
          this.log('⚙️ Конфиг загружен', 'info', `BASE: ${this.baseUrl}`);
        }
      }
    } catch (e) {
      // Молча оставляем дефолтный URL
    }
    if (!this.baseUrl) {
      throw new Error('Не задан адрес backend. Укажите backendBaseUrl в backend.config.json');
    }
  }
  
  async ensureConfig() {
    if (this.configReady) {
      await this.configReady;
    }
    if (!this.baseUrl) {
      throw new Error('Адрес backend не настроен. Проверьте backend.config.json');
    }
  }

  /**
   * Проверка доступности backend
   */
  async checkBackendHealth() {
    await this.ensureConfig();
    try {
      this.log('🔍 Проверка доступности backend...', 'info');
      
      const response = await fetch(`${this.baseUrl}/api/health`, {
        method: 'GET',
        timeout: 5000
      });

      if (!response.ok) {
        throw new Error(`Backend недоступен: HTTP ${response.status}`);
      }

      const health = await response.json();
      this.log('✅ Backend доступен', 'success', `Статус: ${health.status}`);
      
      return health;
    } catch (error) {
      this.log('❌ Backend недоступен', 'error', error.message);
      throw new Error(`Backend сервис недоступен. Убедитесь, что сервис запущен на ${this.baseUrl}`);
    }
  }

  /**
   * Запуск мониторинга статуса парсинга
   */
  startStatusMonitoring() {
    this.log('📊 Запуск мониторинга статуса...', 'info');
    
    // Не запускаем отдельный интервал, так как waitForCompletion() уже проверяет статус
    // Это предотвращает дублирование запросов
  }

  /**
   * Остановка мониторинга статуса
   */
  stopStatusMonitoring() {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval);
      this.statusCheckInterval = null;
      this.log('📊 Мониторинг статуса остановлен', 'info');
    }
  }

  /**
   * Проверка текущего статуса парсинга
   */
  async checkStatus() {
    await this.ensureConfig();
    try {
      const response = await fetch(`${this.baseUrl}/api/status`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const status = await response.json();
      
      // Обновляем прогресс
      if (this.progressCallback && status.progress) {
        this.progressCallback(status.progress);
      }

      // Логируем только важные изменения
      if (status.is_parsing && status.current_case === this.currentCase) {
        // Логируем только если прогресс изменился
        if (status.progress && status.progress !== 'Готов к работе') {
          this.log('📊 Статус парсинга', 'info', status.progress);
        }
      }

      return status;
    } catch (error) {
      this.log('❌ Ошибка получения статуса', 'error', error.message);
      throw error;
    }
  }

  /**
   * Ожидание завершения парсинга
   */
  async waitForCompletion() {
    const maxWaitTime = 600000; // 10 минут (увеличено для сложных случаев)
    const startTime = Date.now();
    let lastStatus = null;
    let parsingStarted = false;
    
    this.log('⏳ Ожидание завершения парсинга...', 'info');
    
    while (Date.now() - startTime < maxWaitTime) {
      try {
        const status = await this.checkStatus();
        
        // Логируем изменения статуса
        if (status.is_parsing && !parsingStarted) {
          parsingStarted = true;
          this.log('🔄 Парсинг начался', 'info', `Дело: ${status.current_case}`);
        }
        
        // Проверяем, завершился ли парсинг
        if (parsingStarted && !status.is_parsing) {
          this.log('✅ Парсинг завершен на backend', 'success', status.progress);
          
          // Получаем ссылки
          const files = await this.getLinks(this.currentCase);
          return {
            success: (files && files.length > 0),
            files: files,
            message: status.progress
          };
        }
        
        // Если парсинг еще не начался, ждем
        if (!parsingStarted) {
          this.log('⏳ Ожидание начала парсинга...', 'info');
        } else {
          // Парсинг в процессе, показываем прогресс
          if (lastStatus === null || lastStatus.progress !== status.progress) {
            this.log('📊 Прогресс парсинга', 'info', status.progress);
            lastStatus = status;
          }
        }
        
        // Ждем перед следующей проверкой
        await this.delay(3000); // Увеличиваем интервал до 3 секунд
        
      } catch (error) {
        this.log('⚠️ Ошибка ожидания завершения', 'warning', error.message);
        await this.delay(5000); // Увеличиваем интервал при ошибках
      }
    }
    
    throw new Error('Превышено время ожидания завершения парсинга (10 минут)');
  }

  /**
   * Получение списка файлов
   */
  async getFilesList() {
    await this.ensureConfig();
    try {
      // Поддержка старого вызова: теперь возвращаем ссылки
      return await this.getLinks(this.currentCase);
    } catch (error) {
      this.log('❌ Ошибка получения ссылок', 'error', error.message);
      return [];
    }
  }

  /**
   * Получение ссылок на документы для дела
   */
  async getLinks(caseNumber) {
    await this.ensureConfig();
    try {
      const response = await fetch(`${this.baseUrl}/api/links?case=${encodeURIComponent(caseNumber)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      const links = Array.isArray(data.links) ? data.links : [];
      // Приводим к унифицированной форме
      const mapped = links.map(link => ({
        name: link.name || 'Document',
        url: link.url,
        date: link.date || null,
        type: link.type || 'PDF',
        note: link.note || ''
      })).filter(item => typeof item.url === 'string' && item.url.toLowerCase().includes('.pdf'));
      this.log('🔗 Получены ссылки', 'success', `Всего: ${mapped.length}`);
      return mapped;
    } catch (error) {
      this.log('❌ Ошибка получения ссылок', 'error', error.message);
      return [];
    }
  }

  /**
   * Скачивание файла
   */
  async downloadFile(filename, url) {
    try {
      this.log('📥 Скачивание файла', 'info', filename);
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      
      // Создаем ссылку для скачивания
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      link.style.display = 'none';
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Освобождаем память
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
      
      this.log('✅ Файл скачан', 'success', filename);
      
    } catch (error) {
      this.log('❌ Ошибка скачивания файла', 'error', `${filename}: ${error.message}`);
      throw error;
    }
  }

  /**
   * Очистка файлов на сервере
   */
  async clearFiles() {
    await this.ensureConfig();
    try {
      this.log('🗑️ Очистка файлов на сервере...', 'info');
      
      const response = await fetch(`${this.baseUrl}/api/clear`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      this.log('✅ Файлы очищены', 'success', result.message);
      
      return result;
    } catch (error) {
      this.log('❌ Ошибка очистки файлов', 'error', error.message);
      throw error;
    }
  }

  /**
   * Получение истории парсинга
   */
  async getHistory() {
    await this.ensureConfig();
    try {
      const response = await fetch(`${this.baseUrl}/api/history`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data.history;
    } catch (error) {
      this.log('❌ Ошибка получения истории', 'error', error.message);
      return [];
    }
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
   * Задержка
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Получение списка скачанных файлов
   */
  getDownloadedFiles() {
    // Совместимость: теперь возвращаем ссылки как "файлы"
    return this.downloadedFiles;
  }

  /**
   * Очистка списка файлов
   */
  clearFiles() {
    this.downloadedFiles = [];
  }

  /**
   * Получение сохраненных страниц с ошибками (заглушка для совместимости)
   */
  getErrorPages() {
    return [];
  }

  /**
   * Очистка сохраненных страниц с ошибками (заглушка для совместимости)
   */
  clearErrorPages() {
    this.log('🗑️ Очистка страниц с ошибками (не применимо для backend)', 'info');
  }
}

// Экспортируем класс для использования
window.BackendClient = BackendClient;
