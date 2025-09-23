/**
 * Основное приложение парсера kad.arbitr.ru для GitHub Pages
 */

class App {
    constructor() {
        this.parser = new KadArbitrParser();
        this.initializeElements();
        this.bindEvents();
        this.checkBrowserCompatibility();
    }

    initializeElements() {
        this.form = document.getElementById('parseForm');
        this.submitBtn = document.getElementById('submitBtn');
        this.caseInput = document.getElementById('case_number');
        this.statusPanel = document.getElementById('statusPanel');
        this.statusText = document.getElementById('statusText');
        this.currentCaseSpan = document.getElementById('currentCase');
        this.progressSpan = document.getElementById('progress');
        this.resultPanel = document.getElementById('resultPanel');
        this.resultIcon = document.getElementById('resultIcon');
        this.resultTitle = document.getElementById('resultTitle');
        this.resultMessage = document.getElementById('resultMessage');
        this.filesSection = document.getElementById('filesSection');
        this.filesList = document.getElementById('filesList');
        this.notification = document.getElementById('notification');
    }

    bindEvents() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    }

    checkBrowserCompatibility() {
        // Проверяем поддержку необходимых API
        const requiredFeatures = [
            'fetch',
            'Blob',
            'URL',
            'Promise'
        ];

        const unsupportedFeatures = requiredFeatures.filter(feature => {
            if (feature === 'fetch') return !window.fetch;
            if (feature === 'Blob') return !window.Blob;
            if (feature === 'URL') return !window.URL;
            if (feature === 'Promise') return !window.Promise;
            return false;
        });

        if (unsupportedFeatures.length > 0) {
            this.showError(`Ваш браузер не поддерживает необходимые функции: ${unsupportedFeatures.join(', ')}. Пожалуйста, обновите браузер.`);
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const caseNumber = this.caseInput.value.trim();
        if (!caseNumber) {
            this.showError('Пожалуйста, введите номер дела');
            return;
        }
        
        // Блокируем форму
        this.submitBtn.disabled = true;
        this.submitBtn.innerHTML = '<span class="spinner"></span> Начинаем парсинг...';
        
        // Скрываем результат
        this.resultPanel.style.display = 'none';
        this.statusPanel.style.display = 'block';
        this.statusPanel.className = 'status-panel parsing';
        
        try {
            const files = await this.parser.parseCase(caseNumber, (progress) => {
                this.updateProgress(caseNumber, progress);
            });
            
            this.showSuccess(`Успешно скачано ${files.length} файлов`, files, caseNumber);
            this.showNotification('Парсинг завершен успешно!', 'success');
            
        } catch (error) {
            console.error('Ошибка парсинга:', error);
            this.showError(`Ошибка парсинга: ${error.message}`, caseNumber);
            this.showNotification('Ошибка парсинга!', 'error');
            
            // Показываем дополнительные советы по устранению ошибок
            this.showErrorTips(error);
        } finally {
            // Разблокируем форму
            this.submitBtn.disabled = false;
            this.submitBtn.innerHTML = '🔍 Найти и скачать файлы';
            this.statusPanel.style.display = 'none';
        }
    }

    updateProgress(caseNumber, progress) {
        this.currentCaseSpan.textContent = caseNumber;
        this.progressSpan.textContent = progress;
    }

    showSuccess(message, files, caseNumber) {
        this.resultPanel.style.display = 'block';
        this.resultPanel.className = 'result-panel success';
        
        this.resultIcon.textContent = '✅';
        this.resultTitle.textContent = 'Парсинг выполнен успешно!';
        this.resultMessage.textContent = message;
        
        // Показываем файлы
        if (files && files.length > 0) {
            this.filesSection.style.display = 'block';
            this.filesList.innerHTML = '';
            
            files.forEach(fileName => {
                const listItem = document.createElement('li');
                listItem.className = 'file-item';
                listItem.innerHTML = `
                    <div class="file-name">📄 ${fileName}</div>
                    <button class="btn-download" onclick="app.downloadFile('${fileName}')">
                        ⬇️ Скачать
                    </button>
                `;
                this.filesList.appendChild(listItem);
            });
        } else {
            this.filesSection.style.display = 'none';
        }
    }

    showError(message, caseNumber = '') {
        this.resultPanel.style.display = 'block';
        this.resultPanel.className = 'result-panel error';
        
        this.resultIcon.textContent = '❌';
        this.resultTitle.textContent = 'Ошибка парсинга';
        this.resultMessage.textContent = message;
        
        this.filesSection.style.display = 'none';
    }

    showErrorTips(error) {
        const errorMessage = error.message.toLowerCase();
        let tips = [];
        
        if (errorMessage.includes('cors') || errorMessage.includes('network')) {
            tips.push('• Проверьте интернет соединение');
            tips.push('• Попробуйте обновить страницу');
            tips.push('• Возможно, сайт временно недоступен');
        } else if (errorMessage.includes('не найдены') || errorMessage.includes('not found')) {
            tips.push('• Проверьте правильность номера дела');
            tips.push('• Убедитесь, что дело существует');
            tips.push('• Попробуйте другой формат номера');
        } else if (errorMessage.includes('timeout') || errorMessage.includes('превышено')) {
            tips.push('• Попробуйте еще раз');
            tips.push('• Проверьте скорость интернета');
            tips.push('• Возможно, сайт перегружен');
        } else {
            tips.push('• Попробуйте обновить страницу');
            tips.push('• Проверьте консоль браузера (F12)');
            tips.push('• Обратитесь к разработчику');
        }
        
        if (tips.length > 0) {
            const tipsHtml = `
                <div style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 8px; text-align: left;">
                    <strong>💡 Советы по устранению:</strong><br>
                    ${tips.join('<br>')}
                </div>
            `;
            this.resultMessage.innerHTML += tipsHtml;
        }
    }

    downloadFile(fileName) {
        // Файлы уже скачаны автоматически, показываем уведомление
        this.showNotification(`Файл ${fileName} уже скачан!`, 'success');
    }

    showNotification(message, type = 'success') {
        this.notification.textContent = message;
        this.notification.className = `notification ${type}`;
        this.notification.classList.add('show');
        
        setTimeout(() => {
            this.notification.classList.remove('show');
        }, 3000);
    }
}

// Инициализация приложения
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new App();
    
    // Показываем информацию о совместимости
    if (navigator.userAgent.includes('Chrome')) {
        console.log('✅ Рекомендуемый браузер: Chrome');
    } else if (navigator.userAgent.includes('Firefox')) {
        console.log('✅ Поддерживаемый браузер: Firefox');
    } else if (navigator.userAgent.includes('Safari')) {
        console.log('✅ Поддерживаемый браузер: Safari');
    } else if (navigator.userAgent.includes('Edge')) {
        console.log('✅ Поддерживаемый браузер: Edge');
    } else {
        console.warn('⚠️ Неизвестный браузер. Возможны проблемы с работой.');
    }
});