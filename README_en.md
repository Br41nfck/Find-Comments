# find_comments.py

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

## By default, only the current folder is scanned

By default, comment search is performed only in the specified folder (no recursion into subfolders). To enable recursive search, use the `--max-depth 0` parameter (or specify the desired depth).

**Example:**

```sh
python find_comments.py --max-depth 0  # search in all subfolders
python find_comments.py --max-depth 2  # search only 2 levels deep
```

---

## License
MIT 