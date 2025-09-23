# 🚀 Инструкция по деплою на GitHub Pages

Подробное руководство по развертыванию парсера kad.arbitr.ru на GitHub Pages.

## 📋 Предварительные требования

- Аккаунт на GitHub
- Git установлен на компьютере
- Node.js версии 14.0.0 или выше
- Браузер (Chrome, Firefox, Safari, Edge)

## 🛠️ Пошаговая инструкция

### Шаг 1: Подготовка репозитория

1. **Создайте новый репозиторий на GitHub:**
   - Перейдите на [github.com](https://github.com)
   - Нажмите "New repository"
   - Название: `kad-arbitr-parser`
   - Описание: `Парсер kad.arbitr.ru для скачивания PDF файлов`
   - Выберите "Public" (обязательно для GitHub Pages)
   - НЕ добавляйте README, .gitignore или лицензию
   - Нажмите "Create repository"

2. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/darkus079/kad-arbitr-parser.git
   cd kad-arbitr-parser
   ```

### Шаг 2: Настройка проекта

1. **Скопируйте файлы проекта:**
   ```bash
   # Скопируйте все файлы из js_parser в папку репозитория
   cp -r /path/to/js_parser/* .
   ```

2. **Установите зависимости:**
   ```bash
   npm install
   ```

3. **Проверьте работу локально:**
   ```bash
   npm start
   ```
   Откройте http://localhost:3000 и убедитесь, что все работает.

### Шаг 3: Настройка GitHub Pages

1. **Перейдите в настройки репозитория:**
   - Откройте ваш репозиторий на GitHub
   - Нажмите на вкладку "Settings"
   - Прокрутите вниз до раздела "Pages"

2. **Настройте источник:**
   - В разделе "Source" выберите "Deploy from a branch"
   - Выберите "main" branch
   - Выберите "/ (root)" folder
   - Нажмите "Save"

3. **Дождитесь активации:**
   - GitHub Pages может потребовать несколько минут для активации
   - Статус будет показан в разделе "Pages"

### Шаг 4: Деплой проекта

1. **Добавьте файлы в Git:**
   ```bash
   git add .
   ```

2. **Сделайте первый коммит:**
   ```bash
   git commit -m "Initial commit: Parser for kad.arbitr.ru"
   ```

3. **Отправьте на GitHub:**
   ```bash
   git push -u origin main
   ```

4. **Дождитесь деплоя:**
   - GitHub автоматически развернет ваш сайт
   - Обычно это занимает 1-5 минут
   - Статус можно проверить во вкладке "Actions"

### Шаг 5: Проверка работы

1. **Откройте ваш сайт:**
   ```
   https://darkus079.github.io/kad-arbitr-parser
   ```

2. **Протестируйте функциональность:**
   - Введите номер дела (например: А81-8566/2025)
   - Нажмите "Найти и скачать файлы"
   - Убедитесь, что файлы скачиваются

## 🔧 Дополнительные настройки

### Настройка кастомного домена (опционально)

1. **Купите домен** у любого регистратора
2. **Настройте DNS:**
   - Создайте CNAME запись: `www` → `darkus079.github.io`
   - Создайте A запись: `@` → `185.199.108.153`
3. **Добавьте файл CNAME:**
   ```bash
   echo "your-domain.com" > CNAME
   git add CNAME
   git commit -m "Add custom domain"
   git push
   ```

### Настройка автоматического деплоя

1. **Создайте GitHub Action:**
   ```yaml
   # .github/workflows/deploy.yml
   name: Deploy to GitHub Pages
   
   on:
     push:
       branches: [ main ]
   
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - name: Deploy to GitHub Pages
           uses: peaceiris/actions-gh-pages@v3
           with:
             github_token: ${{ secrets.GITHUB_TOKEN }}
             publish_dir: .
   ```

2. **Сохраните файл и отправьте:**
   ```bash
   git add .github/workflows/deploy.yml
   git commit -m "Add GitHub Actions workflow"
   git push
   ```

## 🐛 Устранение проблем

### Проблема: Сайт не загружается

**Решение:**
1. Проверьте, что репозиторий публичный
2. Убедитесь, что GitHub Pages включен в настройках
3. Проверьте, что файл `index.html` находится в корне репозитория

### Проблема: Ошибки CORS

**Решение:**
1. Убедитесь, что используется CORS proxy
2. Проверьте, что все запросы идут через HTTPS
3. Обновите браузер до последней версии

### Проблема: Playwright не загружается

**Решение:**
1. Проверьте интернет соединение
2. Убедитесь, что CDN доступен
3. Попробуйте другой браузер

### Проблема: Файлы не скачиваются

**Решение:**
1. Проверьте настройки браузера для скачивания
2. Убедитесь, что всплывающие окна разрешены
3. Проверьте, что сайт kad.arbitr.ru доступен

## 📊 Мониторинг и аналитика

### GitHub Insights

1. **Перейдите в раздел "Insights"** вашего репозитория
2. **Просматривайте статистику:**
   - Количество просмотров
   - Популярные страницы
   - География пользователей

### Google Analytics (опционально)

1. **Добавьте код отслеживания в `index.html`:**
   ```html
   <!-- Google Analytics -->
   <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
   <script>
     window.dataLayer = window.dataLayer || [];
     function gtag(){dataLayer.push(arguments);}
     gtag('js', new Date());
     gtag('config', 'GA_MEASUREMENT_ID');
   </script>
   ```

## 🔄 Обновление сайта

### Автоматическое обновление

1. **Внесите изменения в код**
2. **Отправьте изменения:**
   ```bash
   git add .
   git commit -m "Update: описание изменений"
   git push
   ```
3. **GitHub автоматически обновит сайт**

### Ручное обновление

1. **Перейдите в раздел "Actions"**
2. **Нажмите "Re-run all jobs"**
3. **Дождитесь завершения**

## 📝 Полезные команды

```bash
# Проверка статуса
git status

# Просмотр логов
git log --oneline

# Откат к предыдущей версии
git reset --hard HEAD~1

# Принудительное обновление
git push --force

# Очистка кэша
git clean -fd
```

## 🎯 Оптимизация производительности

### Сжатие файлов

1. **Минификация CSS и JS:**
   ```bash
   npm install -g minify
   minify js/app.js > js/app.min.js
   minify js/parser.js > js/parser.min.js
   ```

2. **Оптимизация изображений:**
   ```bash
   npm install -g imagemin-cli
   imagemin images/* --out-dir=images/optimized
   ```

### Кэширование

1. **Добавьте заголовки кэширования в `.htaccess`:**
   ```apache
   <IfModule mod_expires.c>
     ExpiresActive On
     ExpiresByType text/css "access plus 1 month"
     ExpiresByType application/javascript "access plus 1 month"
     ExpiresByType image/png "access plus 1 month"
   </IfModule>
   ```

## 🚀 Готово!

Ваш парсер kad.arbitr.ru теперь доступен по адресу:
**https://darkus079.github.io/kad-arbitr-parser**

### Что дальше?

1. **Поделитесь ссылкой** с пользователями
2. **Мониторьте работу** через GitHub Insights
3. **Собирайте обратную связь** через Issues
4. **Регулярно обновляйте** код

---

**Удачи с вашим проектом!** 🎉
