/**
 * Клиент для работы с backend API парсера kad.arbitr.ru
 * Заменяет клиентский парсинг на вызовы к backend сервису
 */

class BackendClient {
  constructor() {
    this.baseUrl = 'http://127.0.0.1:8000';
    this.isProcessing = false;
    this.downloadedFiles = [];
    this.progressCallback = null;
    this.logCallback = null;
    this.statusCheckInterval = null;
    this.currentCase = '';
  }

  /**
   * Основной метод парсинга дела через backend
   */
  async parseCase(caseNumber, progressCallback, logCallback) {
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

      this.log('✅ ПАРСИНГ ЗАВЕРШЕН', 'success', `Скачано файлов: ${result.files.length}`);
      return result.files;

    } catch (error) {
      this.log('❌ КРИТИЧЕСКАЯ ОШИБКА', 'error', error.message);
      console.error('❌ Критическая ошибка парсинга:', error);
      throw error;
    } finally {
      this.isProcessing = false;
      this.stopStatusMonitoring();
    }
  }

  /**
   * Проверка доступности backend
   */
  async checkBackendHealth() {
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
    
    this.statusCheckInterval = setInterval(async () => {
      try {
        await this.checkStatus();
      } catch (error) {
        this.log('⚠️ Ошибка проверки статуса', 'warning', error.message);
      }
    }, 2000); // Проверяем каждые 2 секунды
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

      // Логируем изменения
      if (status.is_parsing && status.current_case === this.currentCase) {
        this.log('📊 Статус парсинга', 'info', status.progress);
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
    const maxWaitTime = 300000; // 5 минут
    const startTime = Date.now();
    
    while (Date.now() - startTime < maxWaitTime) {
      try {
        const status = await this.checkStatus();
        
        if (!status.is_parsing) {
          // Парсинг завершен, получаем список файлов
          const files = await this.getFilesList();
          
          return {
            success: status.files_count > 0,
            files: files,
            message: status.progress
          };
        }
        
        // Ждем перед следующей проверкой
        await this.delay(2000);
        
      } catch (error) {
        this.log('⚠️ Ошибка ожидания завершения', 'warning', error.message);
        await this.delay(5000); // Увеличиваем интервал при ошибках
      }
    }
    
    throw new Error('Превышено время ожидания завершения парсинга');
  }

  /**
   * Получение списка файлов
   */
  async getFilesList() {
    try {
      const response = await fetch(`${this.baseUrl}/api/files`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Преобразуем в формат, ожидаемый frontend
      const files = data.files.map(file => ({
        name: file.name,
        size: file.size,
        url: `${this.baseUrl}/api/download/${encodeURIComponent(file.name)}`,
        created: file.created,
        modified: file.modified
      }));

      this.log('📁 Получен список файлов', 'success', `Найдено файлов: ${files.length}`);
      
      return files;
    } catch (error) {
      this.log('❌ Ошибка получения списка файлов', 'error', error.message);
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
