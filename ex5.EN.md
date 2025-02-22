# .ex5 File Format Specification, Version 1.0

**Network Working Group**

Harry Liu

EX5 Team

**Request for Comments**: EX5-001

**Category**: Informational

**Date**: February 2025

**Status of This Memo**

This document specifies an informational protocol for the ex5 community. It does not specify an Internet standard of any kind. Distribution of this memo is unlimited.
Abstract

The .ex5 file format is a novel electronic book container designed to encapsulate book content, multimedia resources, and user interaction data such as reading progress, notes, and ratings. This specification defines Version 1.0 of the .ex5 format, leveraging ZIP archives, JSON, SQLite, and XML to enable secure storage, rich functionality, and remote synchronization. This document provides a detailed protocol for developers to implement .ex5-compliant applications.

**Table of Contents**

1. Introduction (#1-introduction)

   1.1 Purpose (#11-purpose)

   1.2 Scope (#12-scope)

   1.3 Terminology (#13-terminology)

2. Protocol Overview (#2-protocol-overview)

   2.1 File Structure (#21-file-structure)

   2.2 Versioning (#22-versioning)

3. File Format Specification (#3-file-format-specification)

   3.1 Container Format (#31-container-format)

   3.2 book_data Directory (#32-book_data-directory)

   3.3 resources Directory (#33-resources-directory)

   3.4 `read_data.db` SQLite Database (#34-read_datadb-sqlite-database)

   3.5 meta.xml Metadata (#35-metaxml-metadata)
  
4. Encryption and Compression (#4-encryption-and-compression)

   4.1 Encryption Mechanism (#41-encryption-mechanism)

   4.2 Compression Mechanism (#42-compression-mechanism)

5. Remote Synchronization Protocol (#5-remote-synchronization-protocol)

   5.1 Synchronization Overview (#51-synchronization-overview)

   5.2 RESTful API Definition (#52-restful-api-definition)

   5.3 Conflict Resolution (#53-conflict-resolution)

6. Implementation Guidelines (#6-implementation-guidelines)

   6.1 Parsing and Writing .ex5 Files (#61-parsing-and-writing-ex5-files)

   6.2 Example Implementations (#62-example-implementations)

7. Security Considerations (#7-security-considerations)

8. IANA Considerations (#8-iana-considerations)

9. References (#9-references)

10. Acknowledgments (#10-acknowledgments)

## 1. Introduction

#### 1.1 Purpose

The .ex5 file format is designed to provide a robust, extensible, and user-centric solution for electronic books. It aims to:
Store multimedia book content (text, images, audio, video).
Track user interactions (progress, notes, ratings).
Support secure encryption and compression.
Enable synchronization across devices via a remote server.

### 1.2 Scope

This document defines Version 1.0 of the .ex5 protocol, covering file structure, data schemas, encryption, and synchronization mechanisms. Future versions may extend this specification.

### 1.3 Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

## 2. Protocol Overview

### 2.1 File Structure

A .ex5 file is a ZIP archive containing:
book_data/ : Static book metadata and structure.
resources/ : Multimedia resource files.
read_data.db : SQLite database for user data.
meta.xml : Protocol metadata.

### 2.2 Versioning

This specification defines Version 1.0. The version is indicated in the meta.xml file. Future revisions will increment the version number (e.g., 1.1, 2.0) and document changes explicitly.

## 3. File Format Specification

### 3.1 Container Format

Format: ZIP archive (DEFLATED compression).
Extension: .ex5.
Requirement: Implementations MUST support ZIP extraction and creation.

### 3.2 book_data Directory

The book_data/ directory contains three JSON files:

#### 3.2.1 info.json

Defines book metadata:

```json
{
  "title": "STRING (max 1000 chars, UTF-8)",
  "authors": ["STRING"] (max 50 elements),
  "translators": ["STRING"] (max 50 elements, optional),
  "pub_date": INTEGER (Unix timestamp),
  "version": "STRING (max 50 chars)",
  "publisher": "STRING (max 200 chars, optional)",
  "cover_id": INTEGER (0-100),
  "chapter_count": INTEGER (0-100000),
  "word_count": INTEGER (0-10^9)
}
```

#### 3.2.2 chapters.json

Defines chapter structure:

```json
[
  {
    "index": INTEGER (1-100000),
    "title": "STRING (max 500 chars, optional)",
    "resource_ids": [INTEGER] (max 1000 elements, refs resources.json)
  }
]
```

#### 3.2.3 resources.json

Defines resource metadata:

```json
[
  {
    "resource_id": INTEGER (0-1001000),
    "content": "STRING (filename in resources/)",
    "type": "ENUM (txt, image, html, video, sound, binary)",
    "resType": "STRING (max 20 chars, optional, e.g., 'png' for image)"
  }
]
```

- **Constraints:**
  
- 0-1000 reserved for info.json (0-100 for cover, 101-900 reserved).
  - 901-1001000 for content resources.
  
### 3.3 resources Directory

Contains physical resource files (e.g., `cover.png`, `chapter1.txt`). Filenames MUST match the "content" field in resources.json.

### 3.4 read_data.db SQLite Database

A SQLite database with the following tables:

#### 3.4.1 users Table

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier TEXT NOT NULL UNIQUE,
    name TEXT,
    gender TEXT,
    birth_date INTEGER,
    lock INTEGER DEFAULT 0 CHECK (lock IN (0, 1)),
    cipher BLOB
);
```

#### 3.4.2 history Table

```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    read_count INTEGER DEFAULT 1,
    user_id INTEGER NOT NULL,
    start_time INTEGER NOT NULL,
    end_time INTEGER,
    duration INTEGER,
    status INTEGER DEFAULT 0 CHECK (status IN (0, 1, 2)),
    progress TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### 3.4.3 records Table

```sql
CREATE TABLE records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    start_time INTEGER NOT NULL,
    end_time INTEGER NOT NULL,
    progress REAL NOT NULL CHECK (progress >= 0 AND progress <= 100),
    duration INTEGER NOT NULL,
    start_chapter INTEGER,
    end_chapter INTEGER,
    record_time INTEGER NOT NULL,
    FOREIGN KEY (history_id) REFERENCES history(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### 3.4.4 notes Table

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT,
    type TEXT NOT NULL CHECK (type IN ('txt', 'image', 'html', 'video', 'sound', 'binary')),
    create_time INTEGER NOT NULL,
    update_time INTEGER,
    user_id INTEGER NOT NULL,
    chapter_id INTEGER,
    history_id INTEGER,
    records_id INTEGER,
    range_start INTEGER,
    range_end INTEGER,
    original TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (history_id) REFERENCES history(id),
    FOREIGN KEY (records_id) REFERENCES records(id)
);
```

**Notes:**

`content`: For `"txt"`, text string; otherwise, JSON array of `resource_ids`.

`range_start`, `range_end`: Character offsets for highlights (optional).

`original`: Highlighted text (optional).

#### 3.4.5 inspiration Table

```sql
CREATE TABLE inspiration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('txt', 'image', 'html', 'video', 'sound', 'binary')),
    content TEXT,
    create_time INTEGER NOT NULL,
    update_time INTEGER,
    user_id INTEGER NOT NULL,
    chapter_id INTEGER,
    history_id INTEGER,
    records_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (history_id) REFERENCES history(id),
    FOREIGN KEY (records_id) REFERENCES records(id)
);
```

### 3.4.6 reviews Table

```sql
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    create_time INTEGER NOT NULL,
    update_time INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### 3.4.7 ratings Table

```sql
CREATE TABLE ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    create_time INTEGER NOT NULL,
    update_time INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 3.5 meta.xml Metadata

```xml
<?xml version="1.0" encoding="UTF-8"?>
<meta>
  <version>1.0</version>
  <encryption>AES-256</encryption>
  <encrypt_scope>7</encrypt_scope>
</meta>
```

`version`: Protocol version (MUST be "1.0" for this spec).

`encryption`: Encryption algorithm (RECOMMENDED: AES-256).

encrypt_scope: Integer (0-7, 7 = full encryption).

## 4. Encryption and Compression

### 4.1 Encryption Mechanism

- **Targets**: `resources/`, `read_data.db`, or entire file.

- **Algorithm**: AES-256 (default).

- **Scope**:

  - 0: None

  - 4: `resources/` only

  - 5: `resources/` and `book_data/`

  - 6: `resources/` and `read_data.db`

  - 7: Entire file

- **Key**: Derived via PBKDF2 from user password (RECOMMENDED).

### 4.2 Compression Mechanism

- **Target**: Entire `.ex5` file.

- **Algorithm**: ZIP with DEFLATE.

- **Requirement**: Implementations MUST use ZIP compression.

## 5. Remote Synchronization Protocol

### 5.1 Synchronization Overview

**Goal**: Synchronize read_data.db across devices.

**Method**: Incremental updates based on timestamps.

### 5.2 RESTful API Definition

#### 5.2.1 GET /sync/read_data

- **Parameters**:
  - user_id: STRING
  
  - last_sync_time: INTEGER (Unix timestamp)

- **Response**:

```json
{
  "status": "success",
  "data": {
    "users": ARRAY,
    "history": ARRAY,
    "records": ARRAY,
    "notes": ARRAY,
    "inspiration": ARRAY,
    "reviews": ARRAY,
    "ratings": ARRAY
  },
  "timestamp": INTEGER
}
```

#### 5.2.2 POST /sync/read_data

- **Request Body**:

```json
{
  "user_id": STRING,
  "last_sync_time": INTEGER,
  "data": OBJECT (matching read_data.db tables)
}
```

- **Response**:

```json
{
  "status": "success",
  "timestamp": INTEGER
}
```

### 5.3 Conflict Resolution

- **Strategy**: Last-write-wins based on update_time or create_time.

- **Optional**: Manual conflict resolution by user.

## 6. Implementation Guidelines

### 6.1 Parsing and Writing `.ex5` Files

Implementations MUST:

- Extract ZIP archive.
- Parse JSON and XML files.
- Access SQLite database with schema validation.
- Handle encryption as specified.
  
### 6.2 Example Implementations

   **Python Example (Reading Notes)**

```python
import zipfile, sqlite3
with zipfile.ZipFile('book.ex5', 'r') as z:
    z.extract('read_data.db', 'temp/')
conn = sqlite3.connect('temp/read_data.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM notes")
notes = cursor.fetchall()
```

## 7. Security Considerations

- **Encryption**: Use strong keys and secure key management.
- **Synchronization**: Use HTTPS for API calls.
- **Data Validation**: Validate all inputs to prevent injection attacks.

## 8. IANA Considerations

This document does not require IANA action at this time.

## 9. References

[RFC 2119](https://tools.ietf.org/html/rfc2119 "RFC 2119"): Key words for use in RFCs to Indicate Requirement Levels

[SQLite Documentation](https://sqlite.org/ "SQLite")

[ZIP File Format](https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT "ZIP File Format")

## 10.  Acknowledgments

Thanks to the EX5 team for feedback and inspiration.
