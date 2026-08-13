# ex5-format

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.1-green.svg)

The `.ex5` file format is a novel electronic book container designed to encapsulate book content, multimedia resources, and user interaction data such as reading progress, notes, and ratings. Built on ZIP archives with JSON, SQLite, and XML technologies, it supports multimedia embedding, encryption, remote synchronization, and multi-user shared annotations.

## Features

- **Multimedia Support**: Stores text, images, audio, and video resources.
- **User Interaction**: Tracks reading progress, notes (with highlights), comments, inspirations, and ratings.
- **Shared Annotations**: In unencrypted files, notes, excerpts, inspirations, highlights, reviews, and ratings are shared across all users of the book; only the original author can edit (new in 1.1).
- **Resource Management**: Managed via `resources.json` for metadata.
- **Encryption**: Supports AES-256 encryption for content and user data protection.
- **Remote Synchronization**: Implements incremental sync via RESTful API.

## Installation

### Prerequisites

- Python 3.8+
- Dependencies:
  - `zipfile` (built-in)
  - `sqlite3` (built-in)
  - `cryptography` (for encryption)
  - `requests` (for synchronization)

### Install Dependencies

```bash
pip install cryptography requests
```
Usage Examples
Reading Notes from a .ex5 File

```python
import zipfile
import sqlite3

def read_notes(ex5_file):
    with zipfile.ZipFile(ex5_file, 'r') as z:
        z.extract('read_data.db', 'temp/')
    conn = sqlite3.connect('temp/read_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT content, range_start, range_end, original FROM notes")
    notes = cursor.fetchall()
    conn.close()
    return notes
```

# Example

```python
notes = read_notes('example.ex5')
for note in notes:
    print(f"Content: {note[0]}, Range: {note[1]}-{note[2]}, Original: {note[3]}")
```

Creating a .ex5 File

```python
import zipfile
import json
import sqlite3

def create_ex5(filepath, info, chapters, resources, db_data):
    with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('book_data/info.json', json.dumps(info))
        z.writestr('book_data/chapters.json', json.dumps(chapters))
        z.writestr('book_data/resources.json', json.dumps(resources))
        
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, uuid TEXT UNIQUE, content TEXT, type TEXT, create_time INTEGER, user_id INTEGER, range_start INTEGER, range_end INTEGER, original TEXT)")
        cursor.executemany("INSERT INTO notes (uuid, content, type, create_time, user_id, range_start, range_end, original) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", db_data)
        conn.commit()
        dest = sqlite3.connect('temp.db')
        conn.backup(dest)
        dest.close()
        conn.close()
        z.write('temp.db', 'read_data.db')
        
        z.writestr('meta.xml', '<?xml version="1.0" encoding="UTF-8"?><meta><version>1.1</version><encryption>AES-256</encryption><encrypt_scope>7</encrypt_scope></meta>')
```

# Example Data

```python
info = {"title": "Sample Book", "authors": ["Author A"]}
chapters = [{"index": 1, "title": "Chapter 1", "resource_ids": [901]}]
resources = [{"resource_id": 901, "content": "chapter1.txt", "type": "txt", "resType": None}]
db_data = [("b3f1c2a4-9d2e-4f6a-8b1c-0d3e5f7a9b2c", "Sample note", "txt", 1609462800, 1, 10, 20, "Sample highlight")]
create_ex5('example.ex5', info, chapters, resources, db_data)
```

File Structure

```bash
.ex5
├── book_data/
│   ├── info.json       # Book metadata
│   ├── chapters.json   # Chapter information
│   └── resources.json  # Resource metadata
├── resources/          # Resource files (e.g., chapter1.txt)
├── read_data.db        # User data (SQLite, multi-user)
└── meta.xml            # Protocol metadata

```

Protocol Version

Current Version: 1.1 (specified in the version field of meta.xml)

Version 1.1 adds multi-user shared annotations: when the file is not encrypted (encrypt_scope = 0), notes, excerpts, inspirations, highlights, reviews, and ratings of every user are readable by anyone holding the file, while only the original author may edit them.

For the full protocol specification, see RFC EX5-001 (docs/rfc-ex5-001.txt).

Reference Implementation

The `ex5/` package is a reference implementation of spec v1.1 (unencrypted files):

```python
from ex5 import Ex5

# Create a book and add multi-user annotations
book = Ex5.create('example.ex5', info, chapters, resources, resource_files)
book.add_user('alice@example.com', name='Alice')
book.add_user('bob@example.com', name='Bob')
book.add_note('alice@example.com', content='A note', chapter_id=1)
book.save()

# Shared reading: bob sees alice's note; only alice can edit it
with Ex5('example.ex5') as book:
    for note in book.annotations('notes', current_user='bob@example.com'):
        print(note['author_name'], note['content'], 'editable:', note['editable'])
    book.merge('other_copy.ex5')  # merge by identifier + uuid, LWW
```

Run the test suite with `python tests/test_ex5.py`.

Contributing

We welcome contributions, bug reports, and feature suggestions! 
Please follow these steps:

Fork this repository.

Create your feature branch (git checkout -b feature/xxx).

Commit your changes (git commit -m 'Add new feature').

Push to the branch (git push origin feature/xxx).

Open a Pull Request.

License

This project is licensed under the MIT License (LICENSE).

Contact

Email: hl19863129@gmail.com

GitHub Issues: File an issue
