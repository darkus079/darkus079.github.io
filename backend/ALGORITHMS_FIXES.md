# Исправления алгоритмов скачивания PDF для kad.arbitr.ru

## Обзор изменений

На основе анализа сайта kad.arbitr.ru и предоставленной информации о структуре PDF документов, были исправлены следующие алгоритмы:

### Ключевые особенности kad.arbitr.ru:
- **URL структура**: `/Document/Pdf/{guid1}/{guid2}/{filename}.pdf?isAddStamp=True`
- **Chrome PDF Viewer**: Документы отображаются через встроенный Chrome PDF viewer в iframe
- **Кнопка скачивания**: `#save` с диалогом Windows
- **POST запрос**: Требуется для получения PDF данных
- **Shadow DOM**: PDF отображается в закрытом shadow root
- **Таймаут**: 1.5 секунды для загрузки элементов

## Исправленные алгоритмы

### 1. Алгоритм 1: Поиск прямого URL PDF файла ✅

**Проблемы:**
- Не учитывал специфику kad.arbitr.ru с POST запросами
- Неправильные паттерны поиска URL

**Исправления:**
- Добавлен новый метод `_download_pdf_via_post()` для POST запросов
- Обновлены паттерны поиска для специфики kad.arbitr.ru
- Добавлена проверка на прямой PDF URL
- Улучшены заголовки HTTP запросов

**Код изменений:**
```python
# Добавлен новый метод для POST запросов
def _download_pdf_via_post(self, pdf_url, method_name, algorithm_name="unknown"):
    # Пробует разные POST данные:
    # - Пустые данные
    # - {'isAddStamp': 'True'}
    # - {'format': 'pdf'}
    # - {'download': 'true'}
    # - Комбинации параметров

# Обновлены паттерны поиска
pdf_patterns = [
    r'href=["\']([^"\']*Document/Pdf/[0-9a-f-]+/[0-9a-f-]+/[^"\']*\.pdf[^"\']*)["\']',
    r'src=["\']([^"\']*Document/Pdf/[0-9a-f-]+/[0-9a-f-]+/[^"\']*\.pdf[^"\']*)["\']',
    # ... другие специфичные паттерны
]
```

### 2. Алгоритм 2: Извлечение PDF через Selenium автоматизацию ✅

**Проблемы:**
- Не учитывал Chrome PDF Viewer
- Неправильная работа с Shadow DOM kad.arbitr.ru
- Не искал кнопку #save

**Исправления:**
- Обновлен JavaScript для поиска в Shadow DOM kad.arbitr.ru
- Добавлен поиск кнопки #save
- Увеличен таймаут загрузки до 20 секунд
- Добавлена пауза 1.5 секунды для загрузки Shadow DOM
- Заменен `_download_pdf_direct` на `_download_pdf_via_post`

**Код изменений:**
```python
# Обновлен JavaScript для Shadow DOM
js_script = """
function findPdfInShadowDOM() {
    // Ищем template с shadowrootmode="closed"
    const templates = document.querySelectorAll('template[shadowrootmode="closed"]');
    
    // Ищем iframe в template
    const iframe = template.querySelector('iframe[type="application/pdf"]');
    
    // ... остальная логика
}
"""

# Добавлен поиск кнопки #save
save_button = self.driver.find_element(By.CSS_SELECTOR, "#save")
```

### 3. Алгоритм 9: Кнопка "Скачать" + Мониторинг ✅

**Проблемы:**
- Не искал кнопку #save
- Неправильные селекторы для kad.arbitr.ru

**Исправления:**
- Добавлен селектор #save в начало списка
- Уменьшен таймаут до 1.5 секунды
- Улучшена обработка диалога Windows

**Код изменений:**
```python
download_button_selectors = [
    "#save",  # Основная кнопка скачивания
    "button#save",
    "a#save",
    # ... остальные селекторы
]

# Уменьшен таймаут
time.sleep(1.5)  # вместо 5
```

### 4. Алгоритм 12: Методы из autoKad.py ✅

**Проблемы:**
- Использовал GET запросы вместо POST
- Не учитывал специфику kad.arbitr.ru

**Исправления:**
- Заменены все вызовы `_download_pdf_direct` на `_download_pdf_via_post`
- Сохранена логика из autoKad.py

**Код изменений:**
```python
# Заменено во всех местах
files = self._download_pdf_via_post(url, f"autokad_querySelector_{i+1}", "ALGORITHM_12")
```

## Новый метод: _download_pdf_via_post()

Добавлен новый метод для корректной работы с kad.arbitr.ru:

```python
def _download_pdf_via_post(self, pdf_url, method_name, algorithm_name="unknown"):
    """
    Скачивает PDF через POST запрос (специфично для kad.arbitr.ru)
    """
    # Пробует разные POST данные:
    post_data_variants = [
        {},  # Пустые данные
        {'isAddStamp': 'True'},  # С параметром из URL
        {'format': 'pdf'},  # Формат
        {'download': 'true'},  # Флаг скачивания
        {'action': 'download'},  # Действие
        {'isAddStamp': 'True', 'format': 'pdf'},  # Комбинация
        {'isAddStamp': 'True', 'download': 'true'},  # Комбинация
    ]
    
    # Если POST не сработал, пробует GET
    return self._download_pdf_direct(pdf_url, method_name, algorithm_name)
```

## Дополнительные исправления

Следующие алгоритмы также были исправлены:

- **Алгоритм 3**: Перехват сетевых запросов - добавлена поддержка POST запросов через CDP и JavaScript
- **Алгоритм 4**: API запросы - все найденные PDF URL скачиваются через POST запросы
- **Алгоритм 5**: Комплексный подход - использует исправленные алгоритмы 1-4
- **Алгоритм 6**: Продвинутые стратегии - использует AdvancedPDFExtractor с POST поддержкой
- **Алгоритм 7**: PDF.js API - уже корректно работал, изменений не требовалось
- **Алгоритм 8**: Blob URL перехват - уже корректно работал, изменений не требовалось
- **Алгоритм 11**: Ctrl+S + автоматизация диалога - исправлены таймауты и пути

## Рекомендации

1. **Тестирование**: Протестируйте исправленные алгоритмы на реальных документах
2. **Мониторинг**: Следите за логами для выявления проблем
3. **Обновления**: При изменении сайта kad.arbitr.ru может потребоваться обновление алгоритмов
4. **Производительность**: Алгоритм 10 (Print to PDF) остается самым надежным

## Заключение

Исправления направлены на учет специфики kad.arbitr.ru:
- POST запросы вместо GET
- Поиск кнопки #save
- Работа с Shadow DOM
- Правильные таймауты
- Специфичные паттерны URL

Эти изменения должны значительно улучшить успешность скачивания PDF документов с сайта kad.arbitr.ru.
