# Русская документация по find_comments.py

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
---

# ENGLISH DOC find_comments.py

Universal tool for searching, analyzing, and exporting comments in source code.

## Features
- Search for single-line and multi-line comments in many languages.
- Grouping of consecutive comment lines (e.g., /// in C#).
- Filtering by type, content, block length.
- Exclude files by keywords or regex.
- Multithreading and result caching.
- Export to prettytxt, txt, csv, json, html, xlsx, pdf.
- Interactive mode with search, filtering, code preview with syntax highlighting (rich), mass file opening, quick export, copying code with line numbers, opening file at comment line.
- Plugin architecture for new language support.
- Localization: Russian and English.
- --support-lang parameter to display supported languages and comment formats.
- Prints working directory after analysis.

## Installation

Requires Python 3.7+

```sh
pip install colorama prompt_toolkit rich openpyxl reportlab pyperclip
```

- colorama — colored output
- prompt_toolkit — advanced interactive mode (optional)
- rich — code highlighting (optional)
- openpyxl — export to xlsx (optional)
- reportlab — export to pdf (optional)
- pyperclip — copy code to clipboard (optional)

## Supported languages and comment formats

Show the list of supported languages and formats with:
```sh
python find_comments.py --support-lang
```

Example output:
```
  .py     Python            Types: single-line (//, #, ///, ...), multi-line (/* ... */, <!-- ... -->, ...)  Examples: #.*, """ ... """, ''' ... '''
  .js     JavaScript        Types: single-line (//, #, ///, ...), multi-line (/* ... */, <!-- ... -->, ...)  Examples: //.*, /* ... */
  .cs     C#                Types: single-line (//, #, ///, ...), multi-line (/* ... */, <!-- ... -->, ...)  Examples: //.*, ///.*, /* ... */
  ...
```

## Quick start

```sh
python find_comments.py --ext .py .js --contains TODO FIXME
python find_comments.py --ignore test temp --format prettytxt --out comments.txt
python find_comments.py --fail-on TODO --show-content
python find_comments.py --lang en --workers 8 --ignore-regex ".*test.*"
python find_comments.py --include-symbols --format prettytxt --out comments.txt
python find_comments.py --min-lines 3
python find_comments.py --ext .c .cpp --only multi
```

## Interactive mode

```sh
python find_comments.py --interactive
```

### Interactive mode hotkeys

- [→] Next / [←] Prev — navigate comments
- [F]ilter — filter by type
- [S]earch — search by content
- [O]pen file — open current file
- [A]ll open — open all files in selection
- [E]xport — quick export of current selection (md/csv/txt/html/json/pdf)
- [C]opy code — copy code preview with line numbers to clipboard
- [G]o to — open file at comment line (VS Code, Notepad++, Sublime, gedit, default editor)
- [Q]uit — exit

In code preview:
- Line numbers are shown on the left
- Comments are highlighted in green

## Export

```sh
python find_comments.py --report md --report-out report.md
python find_comments.py --report html --report-out report.html
python find_comments.py --report xlsx --report-out report.xlsx
python find_comments.py --report pdf --report-out report.pdf
python find_comments.py --report json --report-out report.json
```

## Plugins

Plugins are .py files exporting a `get_patterns()` function returning a dictionary:

```python
def get_patterns():
    return {
        '.foo': [
            {'type': 'single', 'pattern': r'##.*'},
            {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
        ]
    }
```

Run with plugin:
```sh
python find_comments.py --plugin plugins/myplugin.py --ext .foo
```

## FAQ

**Q: How to add support for a new language?**
A: Use a plugin or extend the COMMENT_PATTERNS dictionary.

**Q: How to speed up analysis of large projects?**
A: Use cache (enabled by default) and increase --workers.

**Q: How to disable colored output?**
A: Use --no-color (if implemented).

**Q: How to export only found comments?**
A: Use --report and filters.

**Q: How to see supported languages?**
A: Run with --support-lang.

## Examples of new features

### Interactive code preview with syntax highlighting and line numbers

```sh
python find_comments.py --interactive
```
- Navigation: arrows, N/P
- Filter by type: F
- Search by content: S
- Code preview with syntax highlighting (rich) and line numbers
- Mass file opening: O (or A in fallback mode)
- Quick export of current selection: E (choose format and filename)
- Copy code with line numbers: C
- Open file at comment line: G

### Export analytics to PDF and JSON

```sh
python find_comments.py --report pdf --report-out report.pdf
python find_comments.py --report json --report-out report.json
```

### Using plugins

```sh
python find_comments.py --plugin plugins/myplugin.py --ext .foo
```

### Quick export from interactive mode

1. Start interactive mode:
   ```sh
   python find_comments.py --interactive
   ```
2. Filter comments (search, filter)
3. Press `E`, choose format (md/csv/txt/html/json/pdf) and filename — only current selection is exported.

### Mass file opening from interactive mode

- Press `O` (or `A` in fallback mode) — all files from current selection will open in the default editor.

---

## License
MIT
