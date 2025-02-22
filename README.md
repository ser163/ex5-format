# ex5-format

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.0-green.svg)

The `.ex5` file format is a novel electronic book container designed to encapsulate book content, multimedia resources, and user interaction data such as reading progress, notes, and ratings. Built on ZIP archives with JSON, SQLite, and XML technologies, it supports multimedia embedding, encryption, and remote synchronization.

## Features

- **Multimedia Support**: Stores text, images, audio, and video resources.
- **User Interaction**: Tracks reading progress, notes (with highlights), comments, inspirations, and ratings.
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
        cursor.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, content TEXT, type TEXT, create_time INTEGER, user_id INTEGER, range_start INTEGER, range_end INTEGER, original TEXT)")
        cursor.executemany("INSERT INTO notes (content, type, create_time, user_id, range_start, range_end, original) VALUES (?, ?, ?, ?, ?, ?, ?)", db_data)
        conn.commit()
        conn.backup(open('temp.db', 'wb'))
        z.write('temp.db', 'read_data.db')
        
        z.writestr('meta.xml', '<?xml version="1.0" encoding="UTF-8"?><meta><version>1.0</version><encryption>AES-256</encryption><encrypt_scope>7</encrypt_scope></meta>')
```

# Example Data

```python
info = {"title": "Sample Book", "authors": ["Author A"]}
chapters = [{"index": 1, "title": "Chapter 1", "resource_ids": [901]}]
resources = [{"resource_id": 901, "content": "chapter1.txt", "type": "txt", "resType": null}]
db_data = [("Sample note", "txt", 1609462800, 1, 10, 20, "Sample highlight")]
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
├── read_data.db        # User data (SQLite)
└── meta.xml            # Protocol metadata

```

Protocol Version

Current Version: 1.0 (specified in the version field of meta.xml)

For the full protocol specification, see RFC EX5-001 (docs/rfc-ex5-001.txt).

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

---

### **Notes**
- **English Version**: Fully translated into English while maintaining clarity and conciseness.
- **GitHub Style**: Includes badges, code blocks, and sections typical of GitHub READMEs (e.g., installation, usage, contributing).
- **Protocol Reference**: Links to a hypothetical RFC document (`docs/rfc-ex5-001.txt`) for detailed specs.
- **Customizable**: You can replace placeholders like email and GitHub repository URL with actual values.