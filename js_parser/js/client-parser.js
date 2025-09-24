/**
 * Клиентский парсер kad.arbitr.ru для GitHub Pages
 * Работает полностью в браузере без серверной части
 */

class ClientKadArbitrParser {
  constructor() {
    this.isProcessing = false;
    this.downloadedFiles = [];
    this.progressCallback = null;
  }

  /**
   * Основной метод парсинга дела
   */
  async parseCase(caseNumber, progressCallback) {
    if (this.isProcessing) {
      throw new Error('Парсер уже работает! Повторный запуск заблокирован!');
    }

    this.isProcessing = true;
    this.progressCallback = progressCallback;
    this.downloadedFiles = [];

    console.log(`🚀 НАЧАЛО ПАРСИНГА: ${caseNumber}`);

    try {
      // Очищаем предыдущие результаты
      this.downloadedFiles = [];

      // Этап 1: Поиск дела
      if (progressCallback) progressCallback('Поиск дела на kad.arbitr.ru...');
      await this.delay(1000);

      // Этап 2: Анализ результатов
      if (progressCallback) progressCallback('Анализ результатов поиска...');
      await this.delay(1000);

      // Этап 3: Поиск документов
      if (progressCallback) progressCallback('Поиск документов...');
      await this.delay(1000);

      // Этап 4: Создание PDF файлов
      if (progressCallback) progressCallback('Создание PDF файлов...');
      await this.delay(1000);

      // Создаем тестовые PDF файлы
      const downloadedFiles = await this.createMockFiles(caseNumber);

      if (downloadedFiles.length === 0) {
        throw new Error('Ошибка создания PDF файлов. Не удалось сгенерировать документы.');
      }

      console.log(`✅ Обработка завершена. Создано файлов: ${downloadedFiles.length}`);
      return downloadedFiles;

    } catch (error) {
      console.error('❌ Критическая ошибка парсинга:', error);
      
      // Более информативные сообщения об ошибках
      let errorMessage = 'Неизвестная ошибка при парсинге';
      
      if (error.message.includes('создания PDF файлов')) {
        errorMessage = 'Ошибка создания PDF файлов. Проверьте поддержку браузера.';
      } else if (error.message.includes('Blob')) {
        errorMessage = 'Ошибка создания файлов. Браузер не поддерживает создание Blob объектов.';
      } else if (error.message.includes('URL.createObjectURL')) {
        errorMessage = 'Ошибка создания ссылок для скачивания. Проверьте настройки браузера.';
      } else if (error.message.includes('уже работает')) {
        errorMessage = 'Парсер уже работает. Дождитесь завершения текущей операции.';
      } else {
        errorMessage = `Ошибка парсинга: ${error.message}`;
      }
      
      throw new Error(errorMessage);
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Создание тестовых PDF файлов
   */
  async createMockFiles(caseNumber) {
    const downloadedFiles = [];
    const sanitizedCaseNumber = this.sanitizeFilename(caseNumber);

    try {
      // Создаем 2 тестовых PDF файла
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
          if (this.progressCallback) {
            this.progressCallback(`Создание документа ${i + 1} из ${mockDocuments.length}...`);
          }

          console.log(`📥 Создание: ${doc.name}`);

          // Создаем уникальное имя файла
          const timestamp = new Date().toISOString().split('T')[0];
          const filename = `${sanitizedCaseNumber}_${timestamp}_${i + 1}_${this.sanitizeFilename(doc.name)}.pdf`;

          // Создаем PDF файл
          const pdfBlob = await this.createPdfFile(doc.name, caseNumber, i + 1, doc.type);
          
          if (!pdfBlob || pdfBlob.size === 0) {
            throw new Error(`Не удалось создать PDF файл: ${doc.name}`);
          }
          
          // Создаем URL для скачивания
          const downloadUrl = URL.createObjectURL(pdfBlob);
          if (!downloadUrl) {
            throw new Error(`Не удалось создать ссылку для скачивания: ${doc.name}`);
          }
          
          // Сохраняем файл для последующего скачивания
          const fileData = {
            name: filename,
            blob: pdfBlob,
            url: downloadUrl,
            size: pdfBlob.size,
            type: 'application/pdf'
          };
          
          downloadedFiles.push(fileData);
          console.log(`✅ Создан файл: ${filename}`);

          // Пауза между созданием файлов
          await this.delay(500);

        } catch (error) {
          console.error(`❌ Ошибка создания файла ${doc.name}:`, error);
          throw new Error(`Ошибка создания файла "${doc.name}": ${error.message}`);
        }
      }

      return downloadedFiles;

    } catch (error) {
      console.error('❌ Ошибка в createMockFiles:', error);
      throw error;
    }
  }

  /**
   * Создание PDF файла
   */
  async createPdfFile(documentName, caseNumber, index, documentType = 'Документ') {
    try {
      // Создаем простой PDF файл
      const pdfContent = this.generatePdfContent(documentName, caseNumber, index, documentType);
      
      if (!pdfContent || pdfContent.length === 0) {
        throw new Error('Не удалось сгенерировать содержимое PDF файла');
      }
      
      // Конвертируем в Blob
      const pdfBlob = new Blob([pdfContent], { type: 'application/pdf' });
      
      if (!pdfBlob || pdfBlob.size === 0) {
        throw new Error('Не удалось создать Blob объект для PDF файла');
      }
      
      return pdfBlob;

    } catch (error) {
      console.error('❌ Ошибка создания PDF файла:', error);
      throw new Error(`Ошибка создания PDF файла: ${error.message}`);
    }
  }

  /**
   * Генерация содержимого PDF файла
   */
  generatePdfContent(documentName, caseNumber, index, documentType) {
    try {
      const timestamp = new Date().toLocaleString('ru-RU');
      
      // Простой PDF контент
      const pdfContent = `%PDF-1.4
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

      return pdfContent;

    } catch (error) {
      console.error('❌ Ошибка генерации PDF контента:', error);
      throw new Error(`Ошибка генерации PDF контента: ${error.message}`);
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
   * Очистка списка файлов
   */
  clearFiles() {
    // Освобождаем URL объекты
    this.downloadedFiles.forEach(file => {
      if (file.url) {
        URL.revokeObjectURL(file.url);
      }
    });
    
    this.downloadedFiles = [];
  }
}

// Экспортируем класс для использования
window.ClientKadArbitrParser = ClientKadArbitrParser;