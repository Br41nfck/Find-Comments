# find_comments.py

Универсальный инструмент для поиска, анализа и экспорта комментариев в исходном коде.

## Возможности
- Поиск однострочных и многострочных комментариев во множестве языков.
- Группировка подряд идущих комментариев (например, /// в C#).
- Фильтрация по типу, содержимому, длине блока.
- Исключение файлов по словам или regex.
- Многопоточность и кэширование.
- Экспорт в prettytxt, txt, csv, json, html, xlsx, pdf.
- Интерактивный просмотр с поиском, фильтрацией, предпросмотром кода с подсветкой (rich), массовым открытием файлов, быстрым экспортом, копированием кода с номерами строк, открытием файла на строке комментария.
- Плагинная архитектура для поддержки новых языков.
- Локализация: русский и английский.
- Параметр --support-lang для вывода поддерживаемых языков и форматов комментариев.
- Вывод рабочей директории после анализа.

## Установка

Требуется Python 3.7+

```sh
pip install colorama prompt_toolkit rich openpyxl reportlab pyperclip
```

- colorama — для цветного вывода
- prompt_toolkit — для продвинутой интерактивности (опционально)
- rich — для подсветки кода (опционально)
- openpyxl — для экспорта в xlsx (опционально)
- reportlab — для экспорта в pdf (опционально)
- pyperclip — для копирования кода в буфер обмена (опционально)

## Поддерживаемые языки и форматы комментариев

Выведите список поддерживаемых языков и форматов командой:
```sh
python find_comments.py --support-lang
```

Пример вывода:
```
  .py     Python            Типы: однострочный (//, #, ///, ...), многострочный (/* ... */, <!-- ... -->, ...)  Примеры: #.*, """ ... """, ''' ... '''
  .js     JavaScript        Типы: однострочный (//, #, ///, ...), многострочный (/* ... */, <!-- ... -->, ...)  Примеры: //.*, /* ... */
  .cs     C#                Типы: однострочный (//, #, ///, ...), многострочный (/* ... */, <!-- ... -->, ...)  Примеры: //.*, ///.*, /* ... */
  ...
```

## Быстрый старт

```sh
python find_comments.py --ext .py .js --contains TODO FIXME
python find_comments.py --ignore test temp --format prettytxt --out comments.txt
python find_comments.py --fail-on TODO --show-content
python find_comments.py --lang en --workers 8 --ignore-regex ".*test.*"
python find_comments.py --include-symbols --format prettytxt --out comments.txt
python find_comments.py --min-lines 3
python find_comments.py --ext .c .cpp --only multi
```

## Интерактивный режим

```sh
python find_comments.py --interactive
```

### Горячие клавиши интерактивного режима

- [→] Next / [←] Prev — переход по комментариям
- [F]ilter — фильтрация по типу
- [S]earch — поиск по содержимому
- [O]pen file — открыть текущий файл
- [A]ll open — массовое открытие всех файлов из выборки
- [E]xport — быстрый экспорт текущей выборки (md/csv/txt/html/json/pdf)
- [C]opy code — скопировать предпросмотр кода с номерами строк в буфер обмена
- [G]o to — открыть файл на строке комментария (VS Code, Notepad++, Sublime, gedit, стандартный редактор)
- [Q]uit — выход

В предпросмотре кода:
- Слева отображаются номера строк исходного файла
- Комментарии выделяются зелёным цветом

## Экспорт

```sh
python find_comments.py --report md --report-out report.md
python find_comments.py --report html --report-out report.html
python find_comments.py --report xlsx --report-out report.xlsx
python find_comments.py --report pdf --report-out report.pdf
python find_comments.py --report json --report-out report.json
```

## Плагины

Плагины — это .py-файлы, экспортирующие функцию `get_patterns()`, возвращающую словарь:

```python
def get_patterns():
    return {
        '.foo': [
            {'type': 'single', 'pattern': r'##.*'},
            {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
        ]
    }
```

Запуск с плагином:
```sh
python find_comments.py --plugin plugins/myplugin.py --ext .foo
```

## Часто задаваемые вопросы (FAQ)

**Q: Как добавить поддержку нового языка?**
A: Через плагин или расширив словарь COMMENT_PATTERNS.

**Q: Как ускорить анализ больших проектов?**
A: Используйте кэш (по умолчанию включён) и увеличьте --workers.

**Q: Как отключить цветной вывод?**
A: Запустите с опцией --no-color (если реализовано).

**Q: Как экспортировать только найденные комментарии?**
A: Используйте --report и фильтры.

**Q: Как посмотреть поддерживаемые языки?**
A: Запустите с --support-lang.

## Примеры новых функций

### Интерактивный предпросмотр с подсветкой кода и номерами строк

```sh
python find_comments.py --interactive
```
- Навигация: стрелки, N/P
- Фильтрация по типу: F
- Поиск по содержимому: S
- Предпросмотр кода с подсветкой (rich) и номерами строк
- Массовое открытие файлов: O (или A в fallback-режиме)
- Быстрый экспорт текущей выборки: E (выберите формат и имя файла)
- Копирование кода с номерами строк: C
- Открытие файла на строке комментария: G

### Экспорт аналитики в PDF и JSON

```sh
python find_comments.py --report pdf --report-out report.pdf
python find_comments.py --report json --report-out report.json
```

### Использование плагинов

```sh
python find_comments.py --plugin plugins/myplugin.py --ext .foo
```

### Быстрый экспорт из интерактивного режима

1. Запустите интерактивный режим:
   ```sh
   python find_comments.py --interactive
   ```
2. Отфильтруйте нужные комментарии (поиск, фильтр)
3. Нажмите `E`, выберите формат (md/csv/txt/html/json/pdf) и имя файла — экспортируется только текущая выборка.

### Массовое открытие файлов из интерактивного режима

- Нажмите `O` (или `A` в fallback-режиме) — откроются все файлы из текущей выборки в редакторе по умолчанию.

---

## Лицензия
MIT
