# Puzzle Project Development Guide

## Data Flow Rule

**All puzzle data must be written to `origin_data/` txt files first, not directly to the database.**

The database (`data/puzzle_data.db`) is derived from txt files via `init_db.py`. The txt files are the single source of truth.

### Adding data flow

1. Write entries to `origin_data/{category}.txt` (e.g. `brain_teaser.txt`, `riddle.txt`)
2. Run `python init_db.py` to load txt data into the database
3. Never insert data directly into SQLite via raw `sqlite3` or SQLAlchemy in production scripts

### Txt file format

```
问题：这里是问题内容
答案:这里是答案内容
---
问题：下一个问题
答案:下一个答案
---
```

- Delimiter between entries: `---` (on its own line)
- Question prefix: `问题：`（full-width colon）
- Answer prefix: `答案:`（half-width colon）
- **Content must not contain standalone `---` or `--` lines**, as they will be misinterpreted as delimiters. Use `——`（em-dash）instead.

### Categories

File name maps to category:

| File | Category |
|---|---|
| `brain_teaser.txt` | `brain_teaser` |
| `riddle.txt` | `riddle` |
| `joke.txt` | `joke` |
| `idiom.txt` | `idiom` |

### Deduplication

Entries are deduplicated via MD5 hash of `"{question}|{answer}"`, stored in the `content_hash` column (unique constraint).

## Project Structure

- `app/` - Flask application (routes, models, utils)
- `origin_data/` - Source txt files (single source of truth for puzzle data)
- `data/` - SQLite database (derived, not manually edited)
- `tools/` - Crawler and utility scripts
- `init_db.py` - Loads `origin_data/*.txt` into database (only when DB is empty)
- `config.py` - App configuration

## Running

```bash
pip install -r requirements.txt
python init_db.py    # Initialize DB from txt files
python app.py        # Start Flask server on :5000
```
