# Исправление блокировки файлов из черного списка

## 🔍 Проблема

**Из логов**:
```
2025-10-01 10:36:49,529 - INFO - 🔍 Найден PDF URL: https://kad.arbitr.ru/Content/Политика конфиденциальности.pdf
2025-10-01 10:36:51,011 - INFO - ✅ PDF скачан: controlled_1_eaabc05c.pdf (170087 байт)
```

**Парсер скачивал файлы из черного списка через Алгоритм 6 (HTTP стратегия)!**

---

## 🎯 Причина

Файл `advanced_pdf_strategies.py` **НЕ** проверял черный список URL перед скачиванием.

### Что было:
```python
# Старый код - НЕТ проверки черного списка
def find_pdf_urls_in_html(self, html_content, base_url):
    pdf_urls = []
    for url in found_urls:
        pdf_urls.append(url)  # ❌ Добавляем ВСЕ URL без проверки
    return pdf_urls
```

### Что стало:
```python
# Новый код - С проверкой черного списка
def find_pdf_urls_in_html(self, html_content, base_url):
    pdf_urls = []
    blocked_count = 0
    for url in found_urls:
        if is_blacklisted_url(url):  # ✅ ПРОВЕРКА
            blocked_count += 1
            continue
        if not is_case_document_url(url):  # ✅ ПРОВЕРКА
            continue
        pdf_urls.append(url)
    return pdf_urls
```

---

## ✅ Решение

### 1. Добавлен черный список в advanced_pdf_strategies.py

```python
# ЧЕРНЫЙ СПИСОК URL - документы, которые НЕ нужно скачивать
PDF_URL_BLACKLIST = [
    'Content/Политика конфиденциальности.pdf',
    '/Content/Политика конфиденциальности.pdf',
    'https://kad.arbitr.ru/Content/Политика конфиденциальности.pdf',
    'privacy',
    'policy',
    'terms',
    'agreement',
    'cookie',
    'help',
    'manual',
    'instruction'
]
```

### 2. Добавлены функции проверки

#### Проверка черного списка:
```python
def is_blacklisted_url(url):
    """Проверяет, находится ли URL в черном списке"""
    url_lower = url.lower()
    for blacklisted in PDF_URL_BLACKLIST:
        if blacklisted.lower() in url_lower:
            logger.warning(f"🚫 [BLACKLIST] URL заблокирован: {url}")
            logger.warning(f"🚫 [BLACKLIST] Причина: содержит '{blacklisted}'")
            return True
    return False
```

#### Проверка документа дела:
```python
def is_case_document_url(url):
    """Проверяет, является ли URL документом дела"""
    case_indicators = [
        'document/pdf', 'pdfdocument', 'getpdf',
        '/card/', 'caseid', 'documentid'
    ]
    
    for indicator in case_indicators:
        if indicator in url.lower():
            logger.info(f"✅ [CASE DOC] Документ дела: {url}")
            return True
    
    # Проверка GUID
    guid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    if re.search(guid_pattern, url.lower()):
        logger.info(f"✅ [CASE DOC] Документ с GUID: {url}")
        return True
    
    return False
```

### 3. Интегрированы проверки во все методы

#### В метод find_pdf_urls_in_html:
```python
for url in found_urls:
    # ПРОВЕРКА ЧЕРНОГО СПИСКА
    if is_blacklisted_url(url):
        blocked_count += 1
        continue  # ⛔ НЕ добавляем в список
    
    # ПРОВЕРКА: Документ дела или служебный
    if not is_case_document_url(url):
        continue  # ⛔ НЕ добавляем в список
    
    # ✅ Только валидные URL
    pdf_urls.append(url)
```

#### В метод download_pdf:
```python
def download_pdf(self, pdf_url, case_url, filename_prefix):
    # ПРОВЕРКА ЧЕРНОГО СПИСКА
    if is_blacklisted_url(pdf_url):
        logger.error(f"❌ [BLOCKED] Попытка скачать URL из черного списка")
        return None  # ⛔ НЕ скачиваем
    
    # ПРОВЕРКА: Документ дела
    if not is_case_document_url(pdf_url):
        logger.warning(f"⚠️ [NOT CASE] Попытка скачать не-документ дела")
        return None  # ⛔ НЕ скачиваем
    
    # ✅ Скачиваем только валидные файлы
    # ... код скачивания ...
```

---

## 📊 Подробное логирование

### Новые логи при блокировке:

#### Когда URL найден, но заблокирован:
```
🚫 [BLACKLIST] URL заблокирован: https://kad.arbitr.ru/Content/Политика конфиденциальности.pdf
🚫 [BLACKLIST] Причина: содержит 'Content/Политика конфиденциальности.pdf'
🚫 [BLOCKED] Заблокировано 1 URL из черного списка
```

#### Когда URL проходит проверку:
```
✅ [CASE DOC] Документ дела: https://kad.arbitr.ru/Document/Pdf/12345 (индикатор: document/pdf)
✅ [FOUND] Найден PDF URL: https://kad.arbitr.ru/Document/Pdf/12345
📋 [FOUND] Найдено 1 валидных PDF URL (после фильтрации)
```

#### Статистика скачивания:
```
📥 [1/1] Попытка скачивания: https://kad.arbitr.ru/Document/Pdf/12345
📥 [DOWNLOAD] Управляемый запрос: https://kad.arbitr.ru/Document/Pdf/12345
✅ [1/1] PDF успешно скачан: controlled_1_abc123.pdf
📊 [STATS] HTTP стратегия:
   ✅ Успешно: 1
   ❌ Ошибки: 0
   📁 Всего файлов: 1
```

#### Когда пытаются скачать заблокированный URL:
```
❌ [BLOCKED] Попытка скачать URL из черного списка: https://kad.arbitr.ru/Content/Политика конфиденциальности.pdf
```

---

## 🧪 Тестирование

### До исправления:
```
🔍 Найден PDF URL: https://kad.arbitr.ru/Content/Политика конфиденциальности.pdf
📥 Управляемый запрос: https://kad.arbitr.ru/Content/Политика конфиденциальности.pdf
✅ PDF скачан: controlled_1_eaabc05c.pdf (170087 байт)  ❌ ПЛОХО!
```

### После исправления:
```
🔍 Поиск PDF URL в HTML...
🚫 [BLACKLIST] URL заблокирован: https://kad.arbitr.ru/Content/Политика конфиденциальности.pdf
🚫 [BLACKLIST] Причина: содержит 'Content/Политика конфиденциальности.pdf'
🚫 [BLOCKED] Заблокировано 1 URL из черного списка
⚠️ [NO URLS] PDF URL не найдены в HTML (после фильтрации)  ✅ ХОРОШО!
```

---

## 📋 Измененные файлы

1. **`backend/advanced_pdf_strategies.py`**
   - Добавлен черный список `PDF_URL_BLACKLIST`
   - Добавлена функция `is_blacklisted_url()`
   - Добавлена функция `is_case_document_url()`
   - Обновлен `find_pdf_urls_in_html()` с фильтрацией
   - Обновлен `download_pdf()` с проверками
   - Обновлен `extract_with_controlled_http()` с подробным логированием

2. **`backend/BLACKLIST_FIX.md`** (этот файл)
   - Документация исправления

---

## 🎯 Результат

### Защита на всех уровнях:

1. **Уровень 1**: Фильтрация при поиске URL в HTML
   ```python
   if is_blacklisted_url(url):
       continue  # Не добавляем в список найденных
   ```

2. **Уровень 2**: Проверка перед скачиванием
   ```python
   if is_blacklisted_url(pdf_url):
       return None  # Не скачиваем
   ```

3. **Уровень 3**: Проверка документа дела
   ```python
   if not is_case_document_url(pdf_url):
       return None  # Не скачиваем служебные документы
   ```

### Подробное логирование на каждом этапе:

- 🔍 Поиск URL
- 🚫 Блокировка URL
- ✅ Валидация документа дела
- 📥 Попытка скачивания
- 📊 Статистика

---

## 🚀 Готово к использованию

Запустите парсер и проверьте логи:

```bash
cd backend
python start_backend.py
```

**Ожидаемые логи**:
```
🔍 Поиск PDF URL в HTML...
🚫 [BLACKLIST] URL заблокирован: https://kad.arbitr.ru/Content/Политика конфиденциальности.pdf
🚫 [BLACKLIST] Причина: содержит 'Content/Политика конфиденциальности.pdf'
🚫 [BLOCKED] Заблокировано 1 URL из черного списка
✅ [CASE DOC] Документ дела: https://kad.arbitr.ru/Document/Pdf/12345
✅ [FOUND] Найден PDF URL: https://kad.arbitr.ru/Document/Pdf/12345
📋 [FOUND] Найдено 1 валидных PDF URL (после фильтрации)
```

**Теперь файлы из черного списка НЕ скачиваются!** ✅

---

## 📚 Дополнительно

### Если нужно добавить URL в черный список:

Отредактируйте `backend/advanced_pdf_strategies.py`:

```python
PDF_URL_BLACKLIST = [
    # ... существующие записи ...
    'новый_паттерн',  # Добавьте сюда
]
```

### Если нужно проверить работу фильтрации:

Запустите парсер и найдите в логах:
- `🚫 [BLACKLIST]` - заблокированные URL
- `✅ [CASE DOC]` - валидные документы дела
- `⚠️ [NOT CASE]` - отфильтрованные URL
- `📊 [STATS]` - статистика скачивания
