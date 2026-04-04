#!/usr/bin/env python3
"""
find_comments.py — универсальный инструмент для поиска и анализа комментариев в исходном коде

Автор: Trix
GitHub: https://github.com/Br41nfck/Find-Comments
Version: 1.5.0

Параметры:
  --root DIR                        Где искать файлы (по умолчанию — текущая папка)
  --ext EXT [EXT ...]               Какие расширения файлов анализировать
  --ignore WORD [...]               Не анализировать файлы, если в имени есть эти слова
  --ignore-regex REGEX              Не анализировать файлы, если имя подходит под regex
  --only TYPE [...]                 Искать только определённые типы комментариев: single, multi, triple_slash, warning
  --contains PATTERN [PATTERN ...]  Только комментарии, содержащие слова/regex
  --min-lines N                     Только блоки длиннее N строк
  --show-progress                   Показывать прогресс (по умолчанию)
  --no-progress                     Не показывать прогресс
  --workers N                       Сколько потоков использовать (по умолчанию 4)
  --out FILE                        Куда сохранить результат
  --format FMT                      Формат вывода: prettytxt, txt, csv, json, html
  --include-symbols                 Оставлять символы комментариев и теги (///, //, #, <summary> и др.)
  --show-content                    Показывать только текст комментариев (без файла/строк)
  --fail-on PATTERN [...]           Завершать с ошибкой, если найден комментарий с этими словами/regex
  --lang LANG                       Язык сообщений: ru (по умолчанию) или en
  --files FILE [FILE ...]           Список файлов для анализа (заменяет --root, --ext и др.)
  --filelist FILE                   Путь к файлу со списком файлов для анализа (по одному в строке)
  --highlight KEY [KEY ...]         Подсвечивать эти слова в выводе (без учёта регистра)
  --max-depth N                     Максимальная глубина рекурсивного обхода директорий (по умолчанию: 1)
  --plugin PLUGIN [PLUGIN ...]      Пути к .py-файлам плагинов (каждый должен экспортировать get_patterns())
  --report TYPE                     Генерировать аналитический отчёт (md, csv, txt, html, xlsx, pdf, json)
  --report-out FILE                 Сохранять отчёт в файл (по умолчанию — вывод в консоль)
  --interactive                     Интерактивный просмотр
  --support-lang                    Показать поддерживаемые языки и форматы комментариев и выйти
  --edit FILE LINE                  Открыть файл в редакторе на нужной строке и выйти
  --version                         Показать версию и выйти

Возможности:
- Находит однострочные и многострочные комментарии во множестве языков программирования.
- Умеет группировать подряд идущие однострочные комментарии (например, /// в C#).
- Позволяет фильтровать комментарии по типу, содержимому, длине блока.
- Работает только с нужными расширениями файлов.
- Может исключать файлы по словам или регулярным выражениям в имени.
- Использует многопоточность для ускорения анализа больших проектов.
- Кэширует результаты для ускорения повторных запусков.
- Красиво выводит результат в консоль (цвета!) и сохраняет в prettytxt, txt, csv, json, html.
- Поддерживает русский и английский языки интерфейса.
- Может использоваться в CI/CD (завершение с ошибкой при определённых комментариях).
- Гибко настраивается через аргументы командной строки.

Примеры использования:
  # Найти TODO и FIXME в Python и JS
  python find_comments.py --ext .py .js --contains TODO FIXME

  # Сохранить prettytxt-отчёт без символов комментариев
  python find_comments.py --ignore test temp --format prettytxt --out comments.txt

  # Завершить с ошибкой, если найден TODO, и вывести только текст
  python find_comments.py --fail-on TODO --show-content

  # Английский язык, 8 потоков, игнорировать файлы с test
  python find_comments.py --lang en --workers 8 --ignore-regex ".*test.*"

  # Сохранить prettytxt-отчёт с символами комментариев
  python find_comments.py --include-symbols --format prettytxt --out comments.txt

  # Только большие блоки (от 3 строк)
  python find_comments.py --min-lines 3

  # Только многострочные комментарии в C/C++
  python find_comments.py --ext .c .cpp --only multi

"""

import os
import re
import argparse
import json
import csv
import hashlib
import datetime
import locale
import sys
import glob
import importlib.util
import subprocess
import shutil
import threading
from collections import Counter, defaultdict
from html import escape
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple, Optional, Set

# Version
VERSION = "1.0.0"

# Try to import optional dependencies
try:
    from colorama import init, Fore, Style as ColoramaStyle
    init(autoreset=True)
except ImportError:
    # Fallback if colorama not installed
    class ColoramaStyle:
        RESET_ALL = ''
    class Fore:
        BLUE = YELLOW = GREEN = RED = MAGENTA = CYAN = ''
    def init(autoreset=True):
        pass

try:
    import openpyxl
    from openpyxl.styles import Font
except ImportError:
    openpyxl = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
except ImportError:
    A4 = canvas = mm = getSampleStyleSheet = SimpleDocTemplate = Paragraph = Spacer = Table = TableStyle = colors = None

try:
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.widgets import Frame
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.shortcuts.dialogs import checkboxlist_dialog
    from prompt_toolkit.shortcuts import input_dialog, message_dialog
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False
    Application = KeyBindings = Layout = HSplit = Window = FormattedTextControl = Frame = Style = HTML = checkboxlist_dialog = input_dialog = message_dialog = None

try:
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = Syntax = Text = None

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    pyperclip = None

# Словарь: расширение -> список паттернов комментариев (однострочные, многострочные)
COMMENT_PATTERNS = {
    '.py': [
        {'type': 'single', 'pattern': r'#.*'},
        {'type': 'multi', 'start': r'"""', 'end': r'"""'},
        {'type': 'multi', 'start': r"'''", 'end': r"'''"},
    ],
    '.js': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.ts': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.tsx': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.java': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.c': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.h': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.cpp': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.hpp': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.cc': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.cxx': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.hxx': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.cs': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'single', 'pattern': r'///.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.go': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.rs': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'single', 'pattern': r'///.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.php': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'single', 'pattern': r'#.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.rb': [
        {'type': 'single', 'pattern': r'#.*'},
    ],
    '.swift': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.kt': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.kts': [
        {'type': 'single', 'pattern': r'//.*'},
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.html': [
        {'type': 'multi', 'start': r'<!--', 'end': r'-->'},
    ],
    '.htm': [
        {'type': 'multi', 'start': r'<!--', 'end': r'-->'},
    ],
    '.xml': [
        {'type': 'multi', 'start': r'<!--', 'end': r'-->'},
    ],
    '.css': [
        {'type': 'multi', 'start': r'/\*', 'end': r'\*/'},
    ],
    '.sh': [
        {'type': 'single', 'pattern': r'#.*'},
    ],
    '.bash': [
        {'type': 'single', 'pattern': r'#.*'},
    ],
    '.md': [
        {'type': 'single', 'pattern': r'<!--.*'},
        {'type': 'multi', 'start': r'<!--', 'end': r'-->'},
    ],
}

LOCALES = {
    'en': {
        'files': 'Files',
        'blocks': 'Comment blocks',
        'warnings': 'Warnings',
        'saved': 'Saved to {out} in {fmt} format.',
        'ci_fail': '[CI/CD] Found {n} comments matching --fail-on. Exiting with error.',
        'help_root': 'Root directory to scan',
        'help_ext': 'File extensions to scan',
        'help_out': 'Output file (if not set, only print to console)',
        'help_format': 'Output format',
        'help_ignore': 'List of words to ignore in file names',
        'help_only': 'Filter by comment type: single, multi, triple_slash, summary, warning',
        'help_min_lines': 'Minimum number of lines in a comment block',
        'help_show_progress': 'Show progress (default)',
        'help_no_progress': 'Do not show progress',
        'help_workers': 'Number of parallel workers (default: 4)',
        'help_ignore_regex': 'Regex pattern to ignore files by name',
        'help_contains': 'Only show comments containing these words or regexes',
        'help_fail_on': 'Exit with error if any comment contains these words or regexes',
        'help_show_content': 'Show only comment text (no file/line info)',
        'help_lang': 'Language for messages (en/ru)',
        'usage': 'Usage: %(prog)s [options]',
        'section_args': 'Arguments',
        'section_opts': 'Options',
        'description': 'find_comments.py — universal tool for searching and analyzing comments in source code.',
        'help_files': 'List of files to scan (overrides --root, --ext, etc.)',
        'help_filelist': 'Path to file with list of files to scan (one per line)',
        'help_highlight': 'Highlight these words in output (case-insensitive)',
        'help_max_depth': 'Maximum directory recursion depth (default: only current folder)',
        'help_plugin': 'Paths to plugin .py files (each must export get_patterns())',
        'help_report': 'Generate analytics report (md, csv, txt, html, xlsx, pdf, json)',
        'help_report_out': 'Report output file (default: print to console)',
        'help_interactive': 'Interactive viewer for comments',
        'help_support_lang': 'Show supported languages and comment formats and exit',
        'help_version': 'Show version and exit',
        'notepadpp_recommend': 'It is recommended to install Notepad++ (https://notepad-plus-plus.org/) for convenient code editing and jumping to lines. Place it in C:/Program Files/Notepad++ or add to PATH.',
    },
    'ru': {
        'files': 'Файлов',
        'blocks': 'Блоков комментариев',
        'warnings': 'Предупреждений',
        'saved': 'Сохранено в {out} в формате {fmt}.',
        'ci_fail': '[CI/CD] Найдено {n} комментариев, соответствующих --fail-on. Завершение с ошибкой.',
        'help_root': 'Корневая папка для поиска',
        'help_ext': 'Расширения файлов для поиска',
        'help_out': 'Файл для сохранения результата (если не задан, только вывод в консоль)',
        'help_format': 'Формат вывода',
        'help_ignore': 'Список слов для игнорирования в именах файлов',
        'help_only': 'Фильтрация по типу комментария: single, multi, triple_slash, summary, warning',
        'help_min_lines': 'Минимальное количество строк в блоке комментария',
        'help_show_progress': 'Показывать прогресс (по умолчанию)',
        'help_no_progress': 'Не показывать прогресс',
        'help_workers': 'Количество параллельных потоков (по умолчанию: 4)',
        'help_ignore_regex': 'Регулярное выражение для игнорирования файлов по имени',
        'help_contains': 'Показывать только комментарии, содержащие эти слова или regex',
        'help_fail_on': 'Завершать с ошибкой, если найден комментарий с этими словами или regex',
        'help_show_content': 'Показывать только текст комментариев (без файла/строк)',
        'help_lang': 'Язык сообщений (en/ru)',
        'usage': 'find_comments.py [опции]',
        'section_args': 'Аргументы',
        'section_opts': 'Опции',
        'description': 'find_comments.py — универсальный инструмент для поиска и анализа комментариев в исходном коде',
        'help_files': 'Список файлов для анализа (заменяет --root, --ext и др.)',
        'help_filelist': 'Путь к файлу со списком файлов для анализа (по одному в строке)',
        'help_highlight': 'Подсвечивать эти слова в выводе (без учёта регистра)',
        'help_max_depth': 'Максимальная глубина рекурсивного обхода директорий (по умолчанию: 1)',
        'help_plugin': 'Пути к .py-файлам плагинов (каждый должен экспортировать get_patterns())',
        'help_report': 'Экспортировать аналитический отчёт (md, csv, txt, html, xlsx, pdf, json)',
        'help_report_out': 'Файл для сохранения отчёта (по умолчанию — вывод в консоль)',
        'help_interactive': 'Интерактивный просмотр комментариев',
        'help_support_lang': 'Показать поддерживаемые языки и форматы комментариев и выйти',
        'help_version': 'Показать версию и выйти',
        'notepadpp_recommend': 'Рекомендуется установить Notepad++ (https://notepad-plus-plus.org/) для удобного редактирования кода и перехода к строкам. Поместите его в C:/Program Files/Notepad++ или добавьте в PATH.',
    }
}


class GitHelpFormatter(argparse.HelpFormatter):
    """Форматтер справки в стиле git"""
    
    def __init__(self, *args, **kwargs):
        kwargs['max_help_position'] = 50
        kwargs['width'] = 200
        super().__init__(*args, **kwargs)

    def _format_action(self, action):
        parts = super()._format_action(action).splitlines()
        if not parts:
            return ''
        while parts and not parts[-1].strip():
            parts.pop()
        return '\n'.join(parts) + '\n'

    def _format_action_invocation(self, action):
        if not action.option_strings:
            return super()._format_action_invocation(action)
        parts = []
        if action.nargs == 0:
            parts.extend(action.option_strings)
        else:
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            for opt in action.option_strings:
                parts.append(f'{opt} {args_string}')
        return ', '.join(parts)


def get_patterns_for_ext(ext: str, plugin_patterns: Dict = None) -> List[Dict]:
    """Возвращает список паттернов комментариев для расширения файла"""
    pats = COMMENT_PATTERNS.get(ext, []).copy()
    if plugin_patterns and ext in plugin_patterns:
        pats.extend(plugin_patterns[ext])
    return pats


def find_comments_in_file(filepath: str, patterns: List[Dict]) -> List[Dict]:
    """Находит все комментарии в файле по заданным паттернам"""
    results = []
    try:
        with open(filepath, encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return results
    
    # Для многострочных комментариев
    for pat in patterns:
        if pat['type'] == 'multi':
            start_pat = re.compile(pat['start'])
            end_pat = re.compile(pat['end'])
            inside = False
            comment_lines = []
            start_line = 0
            for idx, line in enumerate(lines):
                if not inside and start_pat.search(line):
                    inside = True
                    start_line = idx + 1
                    comment_lines = [line.rstrip('\n')]
                    if end_pat.search(line) and start_pat.pattern != end_pat.pattern:
                        results.append({
                            'file': filepath,
                            'line': start_line,
                            'end_line': idx + 1,
                            'text': line.strip(),
                            'type': 'multi',
                        })
                        inside = False
                        comment_lines = []
                elif inside:
                    comment_lines.append(line.rstrip('\n'))
                    if end_pat.search(line):
                        results.append({
                            'file': filepath,
                            'line': start_line,
                            'end_line': idx + 1,
                            'text': '\n'.join(comment_lines),
                            'type': 'multi',
                        })
                        inside = False
                        comment_lines = []
            
            if inside:
                results.append({
                    'file': filepath,
                    'line': start_line,
                    'end_line': len(lines),
                    'text': '\n'.join(comment_lines) + '\n[WARNING: Многострочный комментарий не закрыт!]',
                    'type': 'warning',
                })
    
    # Для однострочных комментариев
    for pat in patterns:
        if pat['type'] == 'single':
            regex = re.compile(pat['pattern'])
            for idx, line in enumerate(lines):
                m = regex.search(line)
                if m:
                    results.append({
                        'file': filepath,
                        'line': idx + 1,
                        'end_line': idx + 1,
                        'text': m.group().strip(),
                        'type': 'single',
                    })
    return results


def file_hash(filepath: str) -> Optional[str]:
    """Вычисляет SHA256-хэш содержимого файла"""
    h = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def load_cache(cache_path: str) -> Dict:
    """Загружает кэш из файла"""
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache_path: str, cache: Dict) -> None:
    """Сохраняет кэш в файл"""
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def clean_comment_line(line: str, include_symbols: bool = False) -> str:
    """Очищает строку комментария от символов комментариев"""
    if include_symbols:
        return line.strip()
    line = re.sub(r'^\s*(///+|//+|#+|/\*+|\*+/)', '', line)
    line = re.sub(r'<\/?summary>', '', line, flags=re.IGNORECASE)
    return line.strip()


def group_comments(comments: List[Dict], include_symbols: bool = False) -> List[Dict]:
    """Группирует подряд идущие комментарии в блоки"""
    grouped = []
    i = 0
    n = len(comments)
    used = set()
    
    while i < n:
        c = comments[i]
        key = (c['file'], c['line'])
        if key in used:
            i += 1
            continue
        
        if c['file'].endswith('.cs') and c['text'].startswith('///'):
            start = i
            end = i
            block_lines = []
            txt = clean_comment_line(c['text'], include_symbols)
            if txt:
                block_lines.append(txt)
            used.add((c['file'], c['line']))
            
            while (end + 1 < n and
                   comments[end + 1]['file'] == c['file'] and
                   comments[end + 1]['line'] == comments[end]['line'] + 1 and
                   comments[end + 1]['text'].startswith('///')):
                end += 1
                txt = clean_comment_line(comments[end]['text'], include_symbols)
                if txt:
                    block_lines.append(txt)
                used.add((comments[end]['file'], comments[end]['line']))
            
            if block_lines:
                grouped.append({
                    'file': c['file'],
                    'start_line': c['line'],
                    'end_line': comments[end]['line'],
                    'lines': block_lines,
                    'type': 'triple_slash',
                })
            i = end + 1
        else:
            txt = clean_comment_line(c['text'], include_symbols)
            if txt:
                grouped.append({
                    'file': c['file'],
                    'start_line': c['line'],
                    'end_line': c['end_line'],
                    'lines': [txt],
                    'type': 'single' if c['line'] == c['end_line'] else 'multi',
                })
            i += 1
    
    return grouped


def highlight_text(text: str, highlight_words: List[str]) -> str:
    """Подсвечивает ключевые слова в тексте"""
    colors = [Fore.RED, Fore.MAGENTA, Fore.CYAN, Fore.YELLOW, Fore.GREEN, Fore.BLUE]
    for i, word in enumerate(highlight_words):
        if not word:
            continue
        color = colors[i % len(colors)] + ColoramaStyle.BRIGHT
        pattern = re.compile(rf'(?i)\b{re.escape(word)}\b')
        text = pattern.sub(lambda m: color + m.group(0) + ColoramaStyle.RESET_ALL, text)
    return text


def print_comments_from_grouped(grouped: List[Dict], show_content: bool = False, 
                                highlight_words: List[str] = None) -> None:
    """Красиво печатает сгруппированные комментарии в консоль"""
    if highlight_words is None:
        highlight_words = ['TODO', 'FIXME', 'BUG', 'HACK', 'NOTE', 'WARNING']
    
    BLUE = Fore.BLUE + ColoramaStyle.BRIGHT
    YELLOW = Fore.YELLOW + ColoramaStyle.BRIGHT
    GREEN = Fore.GREEN + ColoramaStyle.BRIGHT
    RESET = ColoramaStyle.RESET_ALL
    
    for block in grouped:
        lines = [highlight_text(line, highlight_words) for line in block['lines']]
        
        if show_content:
            print(GREEN + '\n'.join(lines) + RESET)
        else:
            if block['start_line'] == block['end_line']:
                print(f"{BLUE}{block['file']}{RESET}:{YELLOW}{block['start_line']}{RESET}: {GREEN}{lines[0]}{RESET}")
            else:
                print(f"{BLUE}{block['file']}{RESET}:{YELLOW}{block['start_line']}-{block['end_line']}{RESET}:")
                print(GREEN + '\n'.join(lines) + RESET)
        print()


# Функции сохранения результатов
def save_csv(comments: List[Dict], filename: str) -> None:
    """Сохраняет результат в CSV-файл"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['file', 'line', 'end_line', 'text'])
        for c in comments:
            writer.writerow([c['file'], c['line'], c['end_line'], c['text']])


def save_json(comments: List[Dict], filename: str) -> None:
    """Сохраняет результат в JSON-файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)


def save_txt(comments: List[Dict], filename: str) -> None:
    """Сохраняет результат в TXT-файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        for c in comments:
            if c['line'] == c['end_line']:
                f.write(f"{c['file']}:{c['line']}: {c['text']}\n")
            else:
                f.write(f"{c['file']}:{c['line']}-{c['end_line']}: {c['text']}\n")


def save_html(comments: List[Dict], filename: str) -> None:
    """Сохраняет результат в HTML-файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<html><head><meta charset="utf-8"><title>Comments</title></head><body>')
        f.write('<table border="1"><tr><th>File</th><th>Line</th><th>End Line</th><th>Text</th></tr>')
        for c in comments:
            f.write(f'<tr><td>{escape(c["file"])}</td><td>{c["line"]}</td><td>{c["end_line"]}</td>'
                   f'<td><pre>{escape(c["text"])}</pre></td></tr>')
        f.write('</table></body></html>')


def save_pretty_txt(comments: List[Dict], filename: str) -> None:
    """Сохраняет результат в prettytxt-файл"""
    grouped = group_comments(comments)
    with open(filename, 'w', encoding='utf-8') as f:
        for block in grouped:
            if block['start_line'] == block['end_line']:
                f.write(f"{block['file']}:{block['start_line']}: {block['lines'][0]}\n")
            else:
                f.write(f"{block['file']}:{block['start_line']}-{block['end_line']}:\n")
                f.write('\n'.join(block['lines']) + '\n')


def save_pretty_txt_from_grouped(grouped: List[Dict], filename: str, root: str, 
                                 files: List[str], warnings: int, errors: List[str]) -> None:
    """Сохраняет prettytxt-отчёт с шапкой"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Directory: {os.path.abspath(root)}\n")
        f.write(f"Datetime: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Files checked: {len(files)}\n")
        f.write(f"Comment blocks: {len(grouped)}\n")
        f.write(f"Warnings: {warnings}\n")
        if errors:
            f.write("Errors:\n")
            for err in errors:
                f.write(f"  {err}\n")
        f.write("\n")
        
        for block in grouped:
            if block['start_line'] == block['end_line']:
                f.write(f"{block['file']}:{block['start_line']}: {block['lines'][0]}\n")
            else:
                f.write(f"{block['file']}:{block['start_line']}-{block['end_line']}:\n")
                f.write('\n'.join(block['lines']) + '\n')


def save_csv_from_grouped(grouped: List[Dict], filename: str) -> None:
    """Сохраняет сгруппированные комментарии в CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['file', 'start_line', 'end_line', 'type', 'text'])
        for block in grouped:
            writer.writerow([block['file'], block['start_line'], block['end_line'], 
                           block['type'], '\n'.join(block['lines'])])


def save_json_from_grouped(grouped: List[Dict], filename: str) -> None:
    """Сохраняет сгруппированные комментарии в JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)


def save_html_from_grouped(grouped: List[Dict], filename: str) -> None:
    """Сохраняет сгруппированные комментарии в HTML"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<html><head><meta charset="utf-8"><title>Comments</title></head><body>')
        f.write('<table border="1"><tr><th>File</th><th>Start Line</th><th>End Line</th><th>Type</th><th>Text</th></tr>')
        for block in grouped:
            f.write(f'<tr><td>{escape(block["file"])}</td><td>{block["start_line"]}</td>'
                   f'<td>{block["end_line"]}</td><td>{block["type"]}</td>'
                   f'<td><pre>{escape("\n".join(block["lines"]))}</pre></td></tr>')
        f.write('</table></body></html>')


def save_txt_from_grouped(grouped: List[Dict], filename: str) -> None:
    """Сохраняет сгруппированные комментарии в TXT"""
    with open(filename, 'w', encoding='utf-8') as f:
        for block in grouped:
            if block['start_line'] == block['end_line']:
                f.write(f"{block['file']}:{block['start_line']}: {block['lines'][0]}\n")
            else:
                f.write(f"{block['file']}:{block['start_line']}-{block['end_line']}: {block['lines'][0]}\n")


def load_plugins(plugin_paths: List[str]) -> Dict:
    """Загружает плагины из списка путей"""
    plugin_patterns = {}
    for path in plugin_paths:
        try:
            spec = importlib.util.spec_from_file_location("plugin_module", path)
            if spec and spec.loader:
                plugin = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin)
                if hasattr(plugin, 'get_patterns'):
                    patterns = plugin.get_patterns()
                    if isinstance(patterns, dict):
                        for ext, pats in patterns.items():
                            if ext not in plugin_patterns:
                                plugin_patterns[ext] = []
                            plugin_patterns[ext].extend(pats)
        except Exception as e:
            print(f"[PLUGIN ERROR] {path}: {e}")
    return plugin_patterns


def generate_report(grouped: List[Dict], files: List[str], report_type: str = 'md', 
                   filename: str = None) -> Optional[str]:
    """Генерирует аналитический отчёт по комментариям"""
    
    # Считаем статистику
    type_counter = Counter()
    file_counter = Counter()
    total_lines = 0
    file_lines = defaultdict(int)
    
    for block in grouped:
        type_counter[block['type']] += 1
        file_counter[block['file']] += 1
    
    for f in files:
        try:
            with open(f, encoding='utf-8', errors='ignore') as ff:
                lines = ff.readlines()
                file_lines[f] = len(lines)
                total_lines += len(lines)
        except Exception:
            pass
    
    comments_total = sum(type_counter.values())
    comments_per_kloc = (comments_total / total_lines * 1000) if total_lines else 0
    
    # Формируем отчёт
    if report_type == 'md':
        lines = [
            '# Аналитика по комментариям',
            '',
            f'- Всего файлов: {len(files)}',
            f'- Всего блоков комментариев: {comments_total}',
            f'- Комментариев на 1000 строк кода: {comments_per_kloc:.2f}',
            '',
            '## Распределение по типам:',
        ]
        for t, n in type_counter.most_common():
            lines.append(f'- **{t}**: {n}')
        lines.append('')
        lines.append('## Топ-10 файлов по количеству комментариев:')
        for f, n in file_counter.most_common(10):
            lines.append(f'- `{f}`: {n} (всего строк: {file_lines.get(f, "?")})')
        lines.append('')
        lines.append('## Распределение по файлам:')
        for f in sorted(file_counter, key=lambda x: -file_counter[x]):
            lines.append(f'- `{f}`: {file_counter[f]} / {file_lines.get(f, "?")} строк')
        report = '\n'.join(lines)
        
    elif report_type == 'csv':
        output = []
        output.append(','.join(['file', 'comments', 'lines']))
        for f in sorted(file_counter, key=lambda x: -file_counter[x]):
            output.append(f"{f},{file_counter[f]},{file_lines.get(f, '?')}")
        report = '\n'.join(output)
        
    elif report_type == 'html':
        lines = [
            '<html><head><meta charset="utf-8"><title>Аналитика по комментариям</title></head><body>',
            '<h1>Аналитика по комментариям</h1>',
            f'<p>Всего файлов: {len(files)}<br>Всего блоков комментариев: {comments_total}<br>'
            f'Комментариев на 1000 строк кода: {comments_per_kloc:.2f}</p>',
            '<h2>Распределение по типам</h2>',
            '<ul>'
        ]
        for t, n in type_counter.most_common():
            lines.append(f'<li><b>{escape(str(t))}</b>: {n}</li>')
        lines.append('</ul>')
        lines.append('<h2>Топ-10 файлов по количеству комментариев</h2><ul>')
        for f, n in file_counter.most_common(10):
            lines.append(f'<li><code>{escape(f)}</code>: {n} (всего строк: {file_lines.get(f, "?")})</li>')
        lines.append('</ul>')
        lines.append('<h2>Распределение по файлам</h2>')
        lines.append('<table border="1"><tr><th>Файл</th><th>Комментариев</th><th>Строк</th></tr>')
        for f in sorted(file_counter, key=lambda x: -file_counter[x]):
            lines.append(f'<tr><td><code>{escape(f)}</code></td><td>{file_counter[f]}</td>'
                        f'<td>{file_lines.get(f, "?")}</td></tr>')
        lines.append('</table></body></html>')
        report = '\n'.join(lines)
        
    elif report_type == 'xlsx':
        if openpyxl is None:
            print('Для экспорта в xlsx установите пакет openpyxl')
            return None
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Аналитика'
        ws.append(['Файл', 'Комментариев', 'Строк'])
        for f in sorted(file_counter, key=lambda x: -file_counter[x]):
            ws.append([f, file_counter[f], file_lines.get(f, '?')])
        for cell in ws[1]:
            cell.font = Font(bold=True)
        if filename:
            wb.save(filename)
            return None
        else:
            import io
            buf = io.BytesIO()
            wb.save(buf)
            return buf.getvalue()
            
    elif report_type == 'json':
        report = json.dumps({
            'summary': {
                'files': len(files),
                'blocks': comments_total,
                'comments_per_kloc': comments_per_kloc,
                'types': dict(type_counter),
            },
            'top_files': file_counter.most_common(10),
            'files': {f: {'comments': file_counter[f], 'lines': file_lines.get(f, '?')} 
                     for f in file_counter},
            'blocks': grouped,
        }, ensure_ascii=False, indent=2)
        
    elif report_type == 'pdf':
        if None in (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, colors):
            print('Для экспорта в pdf установите пакет reportlab')
            return None
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        
        story = []
        styles = getSampleStyleSheet()
        story.append(Paragraph('Аналитика по комментариям', styles['Title']))
        story.append(Paragraph(f'Всего файлов: {len(files)}<br/>Всего блоков комментариев: {comments_total}<br/>'
                              f'Комментариев на 1000 строк кода: {comments_per_kloc:.2f}', styles['Normal']))
        story.append(Spacer(1, 8))
        story.append(Paragraph('Распределение по типам:', styles['Heading2']))
        data = [['Тип', 'Количество']]
        for t, n in type_counter.most_common():
            data.append([str(t), str(n)])
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))
        story.append(Paragraph('Топ-10 файлов по количеству комментариев:', styles['Heading2']))
        data = [['Файл', 'Комментариев', 'Строк']]
        for f, n in file_counter.most_common(10):
            data.append([f, str(n), str(file_lines.get(f, '?'))])
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))
        story.append(Paragraph('Распределение по файлам:', styles['Heading2']))
        data = [['Файл', 'Комментариев', 'Строк']]
        for f in sorted(file_counter, key=lambda x: -file_counter[x]):
            data.append([f, str(file_counter[f]), str(file_lines.get(f, '?'))])
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        story.append(table)
        
        if filename:
            doc = SimpleDocTemplate(filename, pagesize=A4)
            doc.build(story)
            return None
        else:
            import io
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4)
            doc.build(story)
            return buf.getvalue()
    else:  # txt
        lines = [
            'Аналитика по комментариям',
            f'Всего файлов: {len(files)}',
            f'Всего блоков комментариев: {comments_total}',
            f'Комментариев на 1000 строк кода: {comments_per_kloc:.2f}',
            '',
            'Распределение по типам:',
        ]
        for t, n in type_counter.most_common():
            lines.append(f'- {t}: {n}')
        lines.append('')
        lines.append('Топ-10 файлов по количеству комментариев:')
        for f, n in file_counter.most_common(10):
            lines.append(f'- {f}: {n} (всего строк: {file_lines.get(f, "?")})')
        lines.append('')
        lines.append('Распределение по файлам:')
        for f in sorted(file_counter, key=lambda x: -file_counter[x]):
            lines.append(f'- {f}: {file_counter[f]} / {file_lines.get(f, "?")} строк')
        report = '\n'.join(lines)
    
    if filename and report_type not in ('xlsx', 'pdf'):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        return None
    return report


def preview_code_around_comment(block: Dict, context: int = 3, use_rich: bool = False) -> Tuple[str, int, Optional[str]]:
    """Возвращает код вокруг комментария"""
    try:
        with open(block['file'], encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        start = max(0, block['start_line'] - 1 - context)
        end = min(len(lines), block['end_line'] + context)
        preview = lines[start:end]
        code = ''.join(preview)
        
        if use_rich and RICH_AVAILABLE:
            ext = block['file'].split('.')[-1].lower()
            ext_map = {
                'py': 'python', 'js': 'javascript', 'ts': 'typescript', 'cs': 'csharp', 
                'cpp': 'cpp', 'c': 'c', 'h': 'c', 'java': 'java', 'xml': 'xml', 
                'html': 'html', 'css': 'css', 'sh': 'bash', 'rb': 'ruby', 'php': 'php', 
                'go': 'go', 'rs': 'rust', 'swift': 'swift', 'kt': 'kotlin', 'json': 'json',
            }
            language = ext_map.get(ext, ext)
            return code, start + 1, language
        return code, start + 1, None
    except Exception as e:
        return f'[Ошибка предпросмотра кода: {e}]', 1, None


def find_comment_block_in_code(code_lines: List[str], comment_lines: List[str]) -> Set[int]:
    """Ищет блок комментария в коде"""
    indices = set()
    if not comment_lines:
        return indices
    
    code_stripped = [line.strip() for line in code_lines]
    comment_stripped = [line.strip() for line in comment_lines if line.strip()]
    n = len(code_stripped)
    m = len(comment_stripped)
    
    for i in range(n - m + 1):
        if code_stripped[i:i+m] == comment_stripped:
            indices.update(range(i, i+m))
    return indices


def clean_comment_for_display(line: str) -> str:
    """Очищает комментарий для отображения"""
    line = re.sub(r'^\s*(///+|//+|#+|/\*+|\*+/|<!--+|-->|<summary>|</summary>)', '', line, flags=re.IGNORECASE)
    line = re.sub(r'<.*?>', '', line)
    return line.strip()


def interactive_viewer(grouped: List[Dict]) -> None:
    """Интерактивный просмотр комментариев"""
    if not PROMPT_TOOLKIT_AVAILABLE:
        # Fallback на простой режим
        _simple_interactive_viewer(grouped)
        return
    
    idx = [0]
    filtered = [grouped]
    filter_type = [None]
    search_term = ['']
    
    style = Style.from_dict({
        'frame': 'bg:#222222 #ffffff',
        'title': 'bold underline',
        'comment': 'ansigreen',
        'code': 'ansigray',
    })
    
    def get_current_block():
        return filtered[0][idx[0]] if filtered[0] else None
    
    def render():
        try:
            block = get_current_block()
            if (not filtered[0] or not isinstance(block, dict) or not block.get('lines') or
                not isinstance(block['lines'], list) or not block.get('file') or
                not isinstance(block.get('start_line'), int)):
                idx[0] = 0
                return [('', 'Нет комментариев для отображения.\n[→] Next  [←] Prev  [F]ilter  [S]earch  [O]pen file  [A]ll open  [E]xport  [C]opy code  [G]o to  [Q]uit')]
            
            lines = []
            lines.append(('class:title', f'Всего блоков: {len(filtered[0])} | Текущий: {idx[0]+1 if filtered[0] else 0}\n'))
            lines.append(('class:title', f'Файл: {block["file"]}  Строки: {block["start_line"]}-{block["end_line"]}  Тип: {block["type"]}\n'))
            lines.append(('class:title', 'Комментарий:\n'))
            
            for l in block['lines']:
                pretty = clean_comment_for_display(l)
                if pretty:
                    lines.append(('class:comment', pretty + '\n'))
            
            lines.append(('class:title', 'Код вокруг комментария:\n'))
            code, start_line, lang = preview_code_around_comment(block, context=3, use_rich=True)
            code_lines = code.splitlines(keepends=True)
            comment_lines = [line for line in block['lines'] if line.strip()]
            comment_indices = find_comment_block_in_code([l.rstrip('\n') for l in code_lines], comment_lines)
            
            for i, line in enumerate(code_lines):
                lineno = f'{start_line + i:>4} | '
                comment_match = re.search(r'(//|#|/\*|<!--|-->)', line)
                if comment_match:
                    start = comment_match.start()
                    before = line[:start]
                    comment = line[start:].rstrip('\n')
                    lines.append(('class:code', lineno + before))
                    lines.append(('class:comment', comment + '\n'))
                else:
                    lines.append(('class:code', lineno + line.rstrip('\n') + '\n'))
            
            lines.append(('', '\n[→] Next  [←] Prev  [F]ilter  [S]earch  [O]pen file  [A]ll open  [E]xport  [C]opy code  [G]o to  [Q]uit'))
            return lines
        except Exception as e:
            idx[0] = 0
            return [('', f'Нет комментариев для отображения (ошибка: {e}).\n[→] Next  [←] Prev  [F]ilter  [S]earch  [O]pen file  [A]ll open  [E]xport  [C]opy code  [G]o to  [Q]uit')]
    
    kb = KeyBindings()
    
    @kb.add('right')
    def _(event):
        if filtered[0]:
            idx[0] = (idx[0] + 1) % len(filtered[0])
            event.app.invalidate()
    
    @kb.add('left')
    def _(event):
        if filtered[0]:
            idx[0] = (idx[0] - 1) % len(filtered[0])
            event.app.invalidate()
    
    @kb.add('f')
    async def _(event):
        allowed_types = [
            ('single', 'single'),
            ('multi', 'multi'),
            ('triple_slash', 'triple_slash'),
            ('summary', 'summary'),
            ('warning', 'warning')
        ]
        result = await checkboxlist_dialog(
            title='Фильтр по типу',
            text='Выберите типы комментариев для фильтрации (пробел — выбрать, Enter — применить, Esc — сброс):',
            values=allowed_types
        ).run_async()
        if result:
            filtered[0] = [b for b in grouped if b['type'] in result]
            idx[0] = 0
            filter_type[0] = ','.join(result)
        else:
            filtered[0] = grouped
            idx[0] = 0
            filter_type[0] = None
        event.app.invalidate()
    
    @kb.add('s')
    async def _(event):
        s = await input_dialog(title='Поиск', text='Поиск (пусто — сброс):').run_async()
        if s:
            filtered[0] = [b for b in grouped if any(s.lower() in line.lower() for line in b['lines'])]
            idx[0] = 0
            search_term[0] = s
        else:
            filtered[0] = grouped
            idx[0] = 0
            search_term[0] = ''
        event.app.invalidate()
    
    @kb.add('e')
    async def _(event):
        fmt = await input_dialog(title='Экспорт', text='Формат экспорта (md/csv/txt/html/json/pdf):').run_async()
        fname = await input_dialog(title='Экспорт', text='Имя файла для экспорта:').run_async()
        if fmt in ('md', 'csv', 'txt', 'html', 'json', 'pdf'):
            generate_report(filtered[0], sorted(set(b['file'] for b in filtered[0])), report_type=fmt, filename=fname)
        event.app.invalidate()
    
    @kb.add('o')
    def _(event):
        block = get_current_block()
        if block:
            try:
                if os.name == 'nt':
                    npp_path = r'C:\Program Files\Notepad++\notepad++.exe'
                    if os.path.exists(npp_path):
                        subprocess.Popen([npp_path, block['file']])
                    else:
                        subprocess.Popen(['notepad.exe', block['file']])
                else:
                    subprocess.Popen(['xdg-open', block['file']])
            except Exception:
                pass
    
    @kb.add('a')
    def _(event):
        files = sorted(set(b['file'] for b in filtered[0]))
        for f in files:
            try:
                if os.name == 'nt':
                    npp_path = r'C:\Program Files\Notepad++\notepad++.exe'
                    if os.path.exists(npp_path):
                        subprocess.Popen([npp_path, f])
                    else:
                        subprocess.Popen(['notepad.exe', f])
                else:
                    subprocess.Popen(['xdg-open', f])
            except Exception:
                pass
    
    @kb.add('c')
    def _(event):
        block = get_current_block()
        if block:
            for_copy = []
            for i, line in enumerate(block['lines']):
                lineno = f'{block["start_line"] + i:>4} | '
                for_copy.append(lineno + line)
            selected_code = '\n'.join(for_copy)
            if PYPERCLIP_AVAILABLE:
                try:
                    pyperclip.copy(selected_code)
                    print(f'Код скопирован в буфер обмена.')
                except Exception as e:
                    print(f'Ошибка копирования: {e}\nКод:\n{selected_code}')
            else:
                print(f'Код для копирования:\n{selected_code}')
    
    @kb.add('g')
    async def _(event):
        block = get_current_block()
        if not block:
            return
        f = os.path.abspath(block['file'])
        line = block['start_line']
        
        try:
            if os.name == 'nt':
                npp = shutil.which('notepad++')
                npp_path = r'C:\Program Files\Notepad++\notepad++.exe'
                code, start_line, lang = preview_code_around_comment(block, context=3)
                code_lines = code.splitlines(keepends=False)
                comment_lines = [line for line in block['lines'] if line.strip()]
                comment_indices = sorted(find_comment_block_in_code([l.rstrip('\n') for l in code_lines], comment_lines))
                
                if comment_indices:
                    goto_line = start_line + comment_indices[0]
                    comment_line = code_lines[comment_indices[0]]
                    match = re.search(r'(//|#|/\*|<!--|-->)', comment_line)
                    goto_col = match.start() + 1 if match else 1
                else:
                    goto_line = block['start_line']
                    goto_col = 1
                
                if npp:
                    subprocess.Popen(['notepad++', f'-n{goto_line}', f'-c{goto_col}', f])
                elif os.path.exists(npp_path):
                    subprocess.Popen([npp_path, f'-n{goto_line}', f'-c{goto_col}', f])
                else:
                    subprocess.Popen(['notepad.exe', f])
            elif shutil.which('code'):
                subprocess.Popen(['code', '-g', f'{f}:{line}'])
            elif shutil.which('subl'):
                subprocess.Popen(['subl', f'{f}:{line}'])
            elif shutil.which('gedit'):
                subprocess.Popen(['gedit', f'+{line}', f])
            else:
                subprocess.Popen(['xdg-open', f])
        except Exception as e:
            await message_dialog(title='Ошибка', text=f'Не удалось открыть файл: {e}').run_async()
    
    @kb.add('q')
    def _(event):
        event.app.exit()
    
    body = Window(content=FormattedTextControl(render), always_hide_cursor=True)
    frame = Frame(body, title='find_comments.py — Interactive')
    layout = Layout(HSplit([frame]))
    app = Application(layout=layout, key_bindings=kb, style=style, full_screen=True)
    app.run()


def _simple_interactive_viewer(grouped: List[Dict]) -> None:
    """Простой интерактивный просмотр (fallback)"""
    idx = 0
    filtered = grouped
    filter_type = None
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f'Всего блоков: {len(filtered)} | Текущий: {idx+1 if filtered else 0}')
        
        if not filtered:
            print('Нет комментариев для отображения.')
        else:
            block = filtered[idx]
            print(f'Файл: {block["file"]}  Строки: {block["start_line"]}-{block["end_line"]}  Тип: {block["type"]}')
            print('-' * 60)
            print('\n'.join(block['lines']))
            print('-' * 60)
            
            code, start_line, _ = preview_code_around_comment(block, context=3)
            code_lines = code.splitlines(keepends=True)
            comment_lines = [line for line in block['lines'] if line.strip()]
            comment_indices = find_comment_block_in_code([l.rstrip('\n') for l in code_lines], comment_lines)
            
            print('Код вокруг комментария:')
            for i, line in enumerate(code_lines):
                lineno = f'{start_line + i:>4} | '
                if i in comment_indices:
                    print('\033[92m' + lineno + line.rstrip('\n') + '\033[0m')
                else:
                    print(lineno + line.rstrip('\n'))
        
        print('[N]ext  [P]rev  [F]ilter type  [O]pen file  [A] Open all  [E] Export  [Q]uit  [C]opy code')
        cmd = input('> ').strip().lower()
        
        if cmd == 'n' and filtered:
            idx = (idx + 1) % len(filtered)
        elif cmd == 'p' and filtered:
            idx = (idx - 1) % len(filtered)
        elif cmd == 'f':
            t = input('Тип (оставьте пустым для сброса): ').strip()
            if t:
                filtered = [b for b in grouped if b['type'] == t]
                idx = 0
                filter_type = t
            else:
                filtered = grouped
                idx = 0
                filter_type = None
        elif cmd == 'o' and filtered:
            f = block['file']
            try:
                if os.name == 'nt':
                    npp_path = r'C:\Program Files\Notepad++\notepad++.exe'
                    if os.path.exists(npp_path):
                        subprocess.Popen([npp_path, f])
                    else:
                        subprocess.Popen(['notepad.exe', f])
                else:
                    subprocess.Popen(['xdg-open', f])
            except Exception as e:
                print(f'Ошибка открытия файла: {e}')
                input('Нажмите Enter...')
        elif cmd == 'a':
            files = sorted(set(b['file'] for b in filtered))
            for f in files:
                try:
                    if os.name == 'nt':
                        npp_path = r'C:\Program Files\Notepad++\notepad++.exe'
                        if os.path.exists(npp_path):
                            subprocess.Popen([npp_path, f])
                        else:
                            subprocess.Popen(['notepad.exe', f])
                    else:
                        subprocess.Popen(['xdg-open', f])
                except Exception as e:
                    print(f'Ошибка открытия файла: {e}')
            input(f'Открыто файлов: {len(files)}. Нажмите Enter...')
        elif cmd == 'e':
            fmt = input('Формат экспорта (md/csv/txt/html/json/pdf): ').strip()
            fname = input('Имя файла для экспорта: ').strip()
            if fmt in ('md', 'csv', 'txt', 'html', 'json', 'pdf'):
                generate_report(filtered, sorted(set(b['file'] for b in filtered)), report_type=fmt, filename=fname)
                input(f'Экспортировано в {fname}. Нажмите Enter...')
            else:
                input('Неподдерживаемый формат. Нажмите Enter...')
        elif cmd == 'c' and filtered:
            block = filtered[idx]
            for_copy = []
            for i, line in enumerate(block['lines']):
                lineno = f'{block["start_line"] + i:>4} | '
                for_copy.append(lineno + line)
            selected_code = '\n'.join(for_copy)
            if PYPERCLIP_AVAILABLE:
                try:
                    pyperclip.copy(selected_code)
                    print(f'Код скопирован в буфер обмена.')
                except Exception as e:
                    print(f'Ошибка копирования: {e}\nКод:\n{selected_code}')
            else:
                print(f'Код для копирования:\n{selected_code}')
            input('Нажмите Enter...')
        elif cmd == 'q':
            break


def print_supported_languages() -> None:
    """Выводит список поддерживаемых языков"""
    ext_lang_map = {
        '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript', '.tsx': 'TypeScript JSX', '.java': 'Java',
        '.c': 'C', '.h': 'C/C++ Header', '.cpp': 'C++', '.hpp': 'C++ Header', '.cc': 'C++', '.cxx': 'C++', 
        '.hxx': 'C++ Header', '.cs': 'C#', '.go': 'Go', '.rs': 'Rust', '.php': 'PHP', '.rb': 'Ruby', 
        '.swift': 'Swift', '.kt': 'Kotlin', '.kts': 'Kotlin Script', '.html': 'HTML', '.htm': 'HTML', 
        '.xml': 'XML', '.css': 'CSS', '.sh': 'Shell', '.bash': 'Bash', '.md': 'Markdown',
    }
    type_examples = {
        'single': 'однострочный (//, #, ///, ...)',
        'multi': 'многострочный (/* ... */, <!-- ... -->, ...)',
        'triple_slash': '/// подряд (C#, Rust)',
        'warning': 'незакрытый многострочный',
    }
    
    print('\nПоддерживаемые языки и форматы комментариев:')
    for ext, patterns in sorted(COMMENT_PATTERNS.items()):
        lang = ext_lang_map.get(ext, ext)
        types = set(p['type'] for p in patterns)
        type_strs = [type_examples.get(t, t) for t in types]
        ex = []
        for p in patterns:
            if p['type'] == 'single':
                ex.append(p.get('pattern', ''))
            elif p['type'] == 'multi':
                ex.append(f"{p.get('start','')} ... {p.get('end','')}")
        print(f"  {ext:6}  {lang:16}  Типы: {', '.join(type_strs)}  Примеры: {', '.join(ex)}")


def get_parser(lang: str) -> argparse.ArgumentParser:
    """Создаёт и возвращает argparse.ArgumentParser с локализацией"""
    L = LOCALES[lang]
    parser = argparse.ArgumentParser(
        description='',
        formatter_class=GitHelpFormatter,
        add_help=False
    )
    parser._positionals.title = L['section_args']
    parser._optionals.title = L['section_opts']
    
    # Группа для основных параметров
    config_group = parser.add_argument_group('Конфигурация' if lang == 'ru' else 'Configuration')
    config_group.add_argument('--root', default='.', help=L['help_root'])
    config_group.add_argument('--ext', nargs='+', default=[
        '.py', '.js', '.ts', '.tsx', '.java', '.c', '.h', '.cpp', '.hpp', '.cc', '.cxx', '.hxx', '.cs',
        '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.kts', '.html', '.htm', '.xml', '.css', '.sh', '.bash', '.md'
    ], help=L['help_ext'])
    config_group.add_argument('--ignore', nargs='*', default=[], help=L['help_ignore'])
    config_group.add_argument('--ignore-regex', default=None, help=L['help_ignore_regex'])
    config_group.add_argument('--format', choices=['csv', 'json', 'html', 'txt', 'prettytxt'], help=L['help_format'])
    config_group.add_argument('--out', help=L['help_out'])
    config_group.add_argument('--lang', default=lang, choices=['en', 'ru'], help=L['help_lang'])
    
    # Остальные опции
    parser.add_argument('-h', '--help', action='help',
                       help='Показать эту справку и выйти' if lang == 'ru' else 'show this help message and exit')
    parser.add_argument('--version', action='version', version=f'find_comments.py version {VERSION}',
                       help=L['help_version'])
    parser.add_argument('--only', nargs='*', default=[], help=L['help_only'])
    parser.add_argument('--min-lines', type=int, default=0, help=L['help_min_lines'])
    parser.add_argument('--show-progress', dest='show_progress', action='store_true', help=L['help_show_progress'])
    parser.add_argument('--no-progress', dest='show_progress', action='store_false', help=L['help_no_progress'])
    parser.add_argument('--workers', type=int, default=4, help=L['help_workers'])
    parser.add_argument('--contains', nargs='*', default=[], help=L['help_contains'])
    parser.add_argument('--fail-on', nargs='*', default=[], help=L['help_fail_on'])
    parser.add_argument('--show-content', action='store_true', help=L['help_show_content'])
    parser.add_argument('--include-symbols', action='store_true', 
                       help='Оставлять символы комментариев и теги' if lang == 'ru' else 'Include comment symbols and tags')
    parser.add_argument('--files', nargs='+', help=L['help_files'])
    parser.add_argument('--filelist', help=L['help_filelist'])
    parser.add_argument('--highlight', nargs='*', default=['TODO', 'FIXME', 'BUG', 'HACK', 'NOTE', 'WARNING'], 
                       help=L['help_highlight'])
    parser.add_argument('--max-depth', type=int, default=1, help=L['help_max_depth'])
    parser.add_argument('--plugin', nargs='*', default=[], help=L['help_plugin'])
    parser.add_argument('--report', choices=['md', 'csv', 'txt', 'html', 'xlsx', 'pdf', 'json'], help=L['help_report'])
    parser.add_argument('--report-out', help=L['help_report_out'])
    parser.add_argument('--interactive', action='store_true', help=L['help_interactive'])
    parser.add_argument('--support-lang', action='store_true', help=L['help_support_lang'])
    parser.add_argument('--edit', nargs=2, metavar=('FILE', 'LINE'), 
                       help='Открыть файл в редакторе на нужной строке и выйти' if lang == 'ru' else 'Open file in editor at given line and exit')
    parser.set_defaults(show_progress=True)
    
    return parser


def main() -> None:
    """Точка входа"""
    # Определяем язык
    if '--lang' in sys.argv:
        lang_idx = sys.argv.index('--lang')
        if lang_idx + 1 < len(sys.argv):
            lang = sys.argv[lang_idx + 1] if sys.argv[lang_idx + 1] in ['en', 'ru'] else None
        else:
            lang = None
    else:
        lang = None
    
    if lang is None:
        sys_lang = locale.getlocale()[0]
        lang = 'ru' if sys_lang and sys_lang.lower().startswith('ru') else 'en'
    
    # Проверка на --support-lang
    if '--support-lang' in sys.argv:
        print_supported_languages()
        sys.exit(0)
    
    # Проверка на --version
    if '--version' in sys.argv:
        print(f"find_comments.py version {VERSION}")
        sys.exit(0)
    
    # Создаём парсер
    parser = get_parser(lang)
    args = parser.parse_args()
    
    L = LOCALES[args.lang]
    
    # Рекомендуется Notepad++ на Windows
    if os.name == 'nt' and shutil.which('notepad++') is None:
        print(f"\033[93m{L['notepadpp_recommend']}\033[0m")
    
    # Собираем список файлов, если указаны --files или --filelist
    files_from_args = []
    if args.files:
        files_from_args.extend(args.files)
    if args.filelist:
        try:
            with open(args.filelist, encoding='utf-8') as f:
                files_from_args.extend([line.strip() for line in f if line.strip()])
        except Exception as e:
            print(f"[ERROR] Не удалось прочитать файл со списком файлов: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Расширяем wildcard пути
    expanded_files = []
    for path in files_from_args:
        if '*' in path or '?' in path or ('[' in path and ']' in path):
            expanded = glob.glob(path, recursive=True)
            expanded_files.extend([os.path.abspath(f) for f in expanded])
        else:
            expanded_files.append(os.path.abspath(path))
    
    # Загружаем плагины
    plugin_patterns = load_plugins(args.plugin) if args.plugin else {}
    
    comments = []
    files = []
    errors = []
    
    if expanded_files:
        # Режим работы с конкретными файлами
        use_cache = True
        cache_path = '.comments_cache.json'
        cache = load_cache(cache_path) if use_cache else {}
        cache_changed = False
        cache_lock = threading.Lock()
        
        script_path = os.path.abspath(__file__)
        files_to_scan = [f for f in expanded_files 
                        if os.path.splitext(f)[1].lower() in set(args.ext) 
                        and os.path.abspath(f) != script_path]
        files = files_to_scan
        
        def process_file(filepath: str) -> List[Dict]:
            nonlocal cache_changed
            patterns = get_patterns_for_ext(os.path.splitext(filepath)[1].lower(), plugin_patterns=plugin_patterns)
            if patterns:
                h = file_hash(filepath)
                with cache_lock:
                    if use_cache and h and filepath in cache and cache[filepath].get('hash') == h:
                        return cache[filepath]['comments']
                try:
                    file_comments = find_comments_in_file(filepath, patterns)
                    if use_cache and h:
                        with cache_lock:
                            cache[filepath] = {'hash': h, 'comments': file_comments}
                            cache_changed = True
                    return file_comments
                except Exception as e:
                    errors.append(f"{filepath}: {e}")
            return []
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(process_file, filepath) for filepath in files_to_scan]
            if args.show_progress:
                from tqdm import tqdm
                for future in tqdm(as_completed(futures), total=len(futures), desc="Processing files"):
                    comments.extend(future.result())
            else:
                for future in as_completed(futures):
                    comments.extend(future.result())
        
        if use_cache and cache_changed:
            save_cache(cache_path, cache)
    else:
        # Рекурсивный обход директории
        ignore_re = re.compile(args.ignore_regex) if args.ignore_regex else None
        all_files = []
        root_depth = args.root.rstrip(os.sep).count(os.sep)
        script_path = os.path.abspath(__file__)
        
        for dirpath, _, filenames in os.walk(args.root):
            if args.max_depth is not None:
                cur_depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
                if cur_depth >= args.max_depth:
                    continue
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                fpath = os.path.join(dirpath, fname)
                if any(word.lower() in fname.lower() for word in args.ignore):
                    continue
                if ignore_re and ignore_re.search(fname):
                    continue
                if ext in set(args.ext) and os.path.abspath(fpath) != script_path:
                    all_files.append(fpath)
        
        files = all_files
        total = len(files)
        use_cache = True
        cache_path = '.comments_cache.json'
        cache = load_cache(cache_path) if use_cache else {}
        cache_changed = False
        cache_lock = threading.Lock()
        
        def process_file_with_idx(idx_file):
            idx, filepath = idx_file
            if args.show_progress:
                print(f"[{idx}/{total}] Обработка файла: {filepath}")
            patterns = get_patterns_for_ext(os.path.splitext(filepath)[1].lower(), plugin_patterns=plugin_patterns)
            if patterns:
                h = file_hash(filepath)
                with cache_lock:
                    if use_cache and h and filepath in cache and cache[filepath].get('hash') == h:
                        return cache[filepath]['comments']
                try:
                    file_comments = find_comments_in_file(filepath, patterns)
                    if use_cache and h:
                        with cache_lock:
                            cache[filepath] = {'hash': h, 'comments': file_comments}
                            cache_changed = True
                    return file_comments
                except Exception as e:
                    errors.append(f"{filepath}: {e}")
            return []
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(process_file_with_idx, (idx, filepath)) 
                      for idx, filepath in enumerate(files, 1)]
            for future in as_completed(futures):
                comments.extend(future.result())
        
        if use_cache and cache_changed:
            save_cache(cache_path, cache)
    
    # Обработка результатов
    try:
        comments.sort(key=lambda c: (c['file'], c['line']))
        grouped = group_comments(comments, include_symbols=args.include_symbols)
        
        # Фильтрация
        if args.only:
            grouped = [g for g in grouped if g['type'] in args.only]
        
        if args.min_lines > 0:
            grouped = [g for g in grouped if len(g['lines']) >= args.min_lines]
        
        if args.contains:
            contains_res = [re.compile(pat, re.IGNORECASE) for pat in args.contains]
            def block_matches(block):
                text = '\n'.join(block['lines'])
                return any(r.search(text) for r in contains_res)
            grouped = [g for g in grouped if block_matches(g)]
        
        # Проверка на fail-on
        exit_code = 0
        if args.fail_on:
            fail_res = [re.compile(pat, re.IGNORECASE) for pat in args.fail_on]
            def block_fails(block):
                text = '\n'.join(block['lines'])
                return any(r.search(text) for r in fail_res)
            failed = [g for g in grouped if block_fails(g)]
            if failed:
                print(f"\n{L['ci_fail'].format(n=len(failed))}")
                exit_code = 1
        
        # Вывод результатов
        print_comments_from_grouped(grouped, show_content=args.show_content, highlight_words=args.highlight)
        
        # Статистика
        files_set = set(g['file'] for g in grouped)
        warnings = sum(1 for g in grouped if g['type'] == 'warning')
        print(f"\n{L['files']}: {len(files_set)} | {L['blocks']}: {len(grouped)} | {L['warnings']}: {warnings}")
        print(f"Текущая рабочая папка: {os.getcwd()}")
        
        # Сохранение результата
        if args.out and args.format:
            save_map = {
                'csv': save_csv,
                'json': save_json,
                'html': save_html,
                'txt': save_txt,
                'prettytxt': save_pretty_txt,
            }
            if args.format == 'prettytxt':
                save_pretty_txt(comments, args.out)
            elif args.format in save_map:
                save_map[args.format](comments, args.out)
                print(L['saved'].format(out=args.out, fmt=args.format))
                print((f"Результат сохранён в: {args.out}" if args.lang == 'ru' else f"Output saved to: {args.out}"))
        
        # Генерация отчёта
        if args.report:
            generate_report(grouped, files, report_type=args.report, filename=args.report_out)
            if not args.report_out:
                report_content = generate_report(grouped, files, report_type=args.report)
                if report_content:
                    print(report_content)
        
        # Интерактивный режим
        if args.interactive:
            interactive_viewer(grouped)
        
        # Режим редактирования
        if args.edit:
            file_path, line_str = args.edit
            try:
                line = int(line_str)
                if line < 1:
                    raise ValueError
            except Exception:
                print(f"[ERROR] Invalid line number: {line_str}. Must be a positive integer.", file=sys.stderr)
                sys.exit(2)
            
            abs_path = os.path.abspath(file_path)
            if not os.path.isfile(abs_path):
                print(f"[ERROR] File not found: {abs_path}", file=sys.stderr)
                sys.exit(3)
            
            if os.name == 'nt':
                editor = shutil.which('notepad++')
                if not editor:
                    default_npp = r'C:\Program Files\Notepad++\notepad++.exe'
                    if os.path.isfile(default_npp):
                        editor = default_npp
                
                if editor:
                    cmd = [editor, f'-n{line}', abs_path]
                else:
                    print('[WARN] Notepad++ not found, using Notepad (no line support)')
                    editor = shutil.which('notepad')
                    if not editor:
                        print('[ERROR] Notepad not found in PATH.', file=sys.stderr)
                        sys.exit(4)
                    cmd = [editor, abs_path]
                
                try:
                    subprocess.Popen(cmd)
                except Exception as e:
                    print(f"[ERROR] Failed to open editor: {e}", file=sys.stderr)
                    sys.exit(5)
            else:
                print('[ERROR] --edit supported only on Windows', file=sys.stderr)
                sys.exit(6)
            sys.exit(0)
        
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
