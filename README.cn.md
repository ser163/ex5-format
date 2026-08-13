# ex5 文件格式

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.1-green.svg)

.ex5 是一种新型电子书文件格式，旨在提供内容存储、用户交互数据管理和跨设备同步的综合解决方案。它基于 ZIP 存档，使用 JSON、SQLite 和 XML 技术，支持多媒体嵌入、加密保护、远程同步和多人共享批注。

## 功能特性

- **多媒体支持**：存储文本、图片、音频、视频等资源。
- **用户交互**：记录阅读进度、笔记（含划线）、评论、灵感和评分。
- **共享批注**：未加密文件中，批注、摘抄、心得、划线、评价和评分对本书所有用户可见，仅原作者可编辑（1.1 新增）。
- **资源管理**：通过 `resources.json` 管理资源元数据。
- **加密保护**：支持 AES-256 加密，保护内容和用户数据。
- **远程同步**：通过 RESTful API 实现增量同步。

## 安装

### 前提条件

- Python 3.8+
  
- 依赖库：
  - `zipfile`（内置）
  - `sqlite3`（内置）
  - `cryptography`（用于加密）
  - `requests`（用于同步）

### 安装依赖

```bash
pip install cryptography requests
```

使用示例

读取 .ex5 文件中的笔记

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

# 示例

```python
notes = read_notes('example.ex5')
for note in notes:
    print(f"内容: {note[0]}, 范围: {note[1]}-{note[2]}, 原文: {note[3]}")
```

创建 .ex5 文件

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

# 示例数据

```python
info = {"title": "示例书籍", "authors": ["作者A"]}
chapters = [{"index": 1, "title": "第一章", "resource_ids": [901]}]
resources = [{"resource_id": 901, "content": "chapter1.txt", "type": "txt", "resType": None}]
db_data = [("b3f1c2a4-9d2e-4f6a-8b1c-0d3e5f7a9b2c", "笔记示例", "txt", 1609462800, 1, 10, 20, "示例划线")]
create_ex5('example.ex5', info, chapters, resources, db_data)
```

文件结构

```bash
.ex5
├── book_data/
│   ├── info.json       # 书籍元数据
│   ├── chapters.json   # 章节信息
│   └── resources.json  # 资源元数据
├── resources/          # 资源文件（如 chapter1.txt）
├── read_data.db        # 用户数据（SQLite，支持多用户）
└── meta.xml            # 协议元数据
```

协议版本

当前版本：1.1（定义于 meta.xml 的 version 字段）

1.1 版新增多人共享批注：当文件未加密（encrypt_scope = 0）时，批注、摘抄、心得、划线、评价和评分对任何持有该文件的用户可读，仅原作者可编辑。

完整的协议规范见 RFC EX5-001 (docs/rfc-ex5-001.txt)。
参考实现

`ex5/` 包是 1.1 版规范的参考实现（支持未加密文件）：

```python
from ex5 import Ex5

# 创建书籍并添加多用户批注
book = Ex5.create('example.ex5', info, chapters, resources, resource_files)
book.add_user('alice@example.com', name='Alice')
book.add_user('bob@example.com', name='Bob')
book.add_note('alice@example.com', content='一条批注', chapter_id=1)
book.save()

# 共享读取：bob 能看到 alice 的批注，但只有 alice 可以编辑
with Ex5('example.ex5') as book:
    for note in book.annotations('notes', current_user='bob@example.com'):
        print(note['author_name'], note['content'], '可编辑:', note['editable'])
    book.merge('other_copy.ex5')  # 按 identifier + uuid 合并，最后写入获胜
```

运行测试：`python tests/test_ex5.py`。

贡献
欢迎贡献代码、提交问题或提出建议！请遵循以下步骤：
Fork 本仓库。
创建您的特性分支（git checkout -b feature/xxx）。
提交更改（git commit -m '添加新特性'）。
推送到分支（git push origin feature/xxx）。
创建 Pull Request。

许可证

本项目依据 MIT 许可证 (LICENSE) 开源。

联系方式

邮箱: Hl19863129@gmail.com

GitHub Issues: 提交问题
