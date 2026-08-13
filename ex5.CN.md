# `.ex5` 文件格式规范，版本 1.1

**网络工作组**

- Harry Liu

- EX5 团队

**请求评论**：EX5-001  
**类别**：信息性  
**日期**：2025 年 2 月（1.1 版修订）

## 本备忘录状态

本文件为 EX5 社区指定了一个信息性协议。它并未指定任何类型的互联网标准。本备忘录的分发不受限制。

## 摘要

.ex5 文件格式是一种新颖的电子书容器，设计用于封装书籍内容、多媒体资源以及用户交互数据（如阅读进度、笔记和评分）。本规范定义了 .ex5 格式的版本 1.1，利用 ZIP 存档、JSON、SQLite 和 XML 实现安全存储、丰富功能和远程同步。1.1 版新增多人共享批注能力：在未加密的文件中，批注、摘抄、心得、划线、评价和评分对所有持有该文件的用户可读，且仅原作者可以编辑。本文档为开发者提供了详细的协议，以实现符合 .ex5 的应用程序。

## 目录

1. 引言
  
   - 1.1 目的

   - 1.2 范围

   - 1.3 术语

2. 协议概览

   - 2.1 文件结构

   - 2.2 版本控制

3. 文件格式规范

   - 3.1 容器格式

   - 3.2 book_data 目录

   - 3.3 resources 目录

   - 3.4 read_data.db SQLite 数据库

   - 3.5 meta.xml 元数据

4. 加密与压缩

   - 4.1 加密机制

   - 4.2 压缩机制

5. 远程同步协议

   - 5.1 同步概览

   - 5.2 RESTful API 定义

   - 5.3 冲突解决

   - 5.4 共享批注与权限

6. 实现指南

   - 6.1 解析和写入 .ex5 文件

   - 6.2 示例实现

7. 安全考虑

8. IANA 考虑

9. 参考文献

10. 致谢

---

## 1. 引言

### 1.1 目的

.ex5 文件格式旨在为电子书提供一个健壮、可扩展、以用户为中心的全方位解决方案。其目标包括：

- 存储多媒体书籍内容（文本、图片、音频、视频）。
- 跟踪用户交互（进度、笔记、评分）。
- 支持安全加密和压缩。
- 通过远程服务器实现跨设备同步。
- 支持多人共享批注、摘抄、心得、划线、评价与评分（仅限未加密文件）。

### 1.2 范围

本文档定义了 .ex5 协议的版本 1.1，涵盖文件结构、数据模式、加密和同步机制。未来的版本可能会扩展此规范。

### 1.3 术语

本文档中的关键词“必须”、“不得”、“必需”、“应当”、“不应当”、“应该”、“不应该”、“推荐”、“可以”和“可选”应按照 RFC 2119 的描述进行解释。

---

## 2. 协议概览

### 2.1 文件结构

.ex5 文件是一个 ZIP 存档，包含以下内容：

- `book_data/`：静态书籍元数据和结构。
- `resources/`：多媒体资源文件。
- `read_data.db`：用户数据的 SQLite 数据库。
- `meta.xml`：协议元数据。

### 2.2 版本控制

本规范定义了版本 1.1。版本信息在 meta.xml 文件中指定。未来的修订将递增版本号（例如 1.2、2.0）并明确记录变更。

1.1 版相对 1.0 版的变更：

- 新增多人共享批注与权限模型（5.4 节）：未加密文件中，所有用户的批注、摘抄、心得、划线、评价和评分互相可读，仅原作者可编辑。
- notes、inspiration、reviews、ratings 表新增 `uuid` 字段，用于跨用户、跨设备合并时的去重。
- 明确资源 ID 区间划分、encrypt_scope 保留值、加密算法细节及 meta.xml 的明文要求。

---

## 3. 文件格式规范

### 3.1 容器格式

- 格式：ZIP 存档（使用 DEFLATED 压缩）。
- 扩展名：.ex5。
- 要求：实现必须支持 ZIP 的提取和创建。

### 3.2 book_data 目录

book_data/ 目录包含三个 JSON 文件：

#### 3.2.1 info.json

定义书籍元数据：

```json
{
  "title": "字符串 (最大 1000 字符, UTF-8)",
  "authors": ["字符串"] (最多 50 个元素),
  "translators": ["字符串"] (最多 50 个元素，可选),
  "pub_date": 整数 (Unix 时间戳),
  "version": "字符串 (最大 50 字符)",
  "publisher": "字符串 (最大 200 字符，可选)",
  "cover_id": 整数 (0-100),
  "chapter_count": 整数 (0-100000),
  "word_count": 整数 (0-10^9)
}
```

#### 3.2.2 chapters.json

定义章节结构：

```json
[
  {
    "index": 整数 (1-100000),
    "title": "字符串 (最大 500 字符，可选)",
    "resource_ids": [整数] (最多 1000 个元素，引用 resources.json)
  }
]
```

#### 3.2.3 resources.json

定义资源元数据：

```json
[
  {
    "resource_id": 整数 (0-1001000),
    "content": "字符串 (resources/ 中的文件名)",
    "type": "枚举 (txt, image, html, video, sound, binary)",
    "resType": "字符串 (最大 20 字符，可选，例如 image 的 'png')"
  }
]
```

约束：

- 0-100：封面资源（由 info.json 的 cover_id 字段引用）。
- 101-900：保留，供未来版本使用；实现不得在该区间分配内容资源。
- 901-1001000：内容资源。

### 3.3 resources 目录

包含物理资源文件（例如 cover.png、chapter1.txt）。文件名必须与 resources.json 中的 "content" 字段匹配。

### 3.4 read_data.db SQLite 数据库

SQLite 数据库包含以下表。read_data.db 通过 users 表天然支持多用户：同一本书的多个用户的批注、心得、评价等数据共存于同一数据库中，共享语义见 5.4 节。

#### 3.4.1 users 表

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

#### 3.4.2 history 表

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

备注：`progress` 以文本形式存储最近一次阅读的进度摘要，推荐使用 JSON 编码的对象（例如 `{"chapter": 3, "offset": 128}`），以便与 records 表中的数值进度区分开。

#### 3.4.3 records 表

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

#### 3.4.4 notes 表

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE,
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

备注：

- content：对于 "txt"，是文本字符串；其他类型为 resource_ids 的 JSON 数组。
- range_start, range_end：划线字符偏移量（可选）。
- original：划线文本（可选）。
- chapter_id：对应 chapters.json 中的章节 index（章节定义在 JSON 中而非数据库内，故无外键约束）。
- uuid：记录的全局唯一标识（推荐 UUID v4），创建时生成，用于跨用户、跨设备合并时的去重与冲突解决（见 5.4 节）。
- 功能映射：批注 = 含 content 的记录；摘抄 = 含 original 与 range_start/range_end 的记录；划线 = 仅含 range_start/range_end 而无 content 的记录。

#### 3.4.5 inspiration 表

```sql
CREATE TABLE inspiration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE,
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

备注：uuid 字段语义同 notes 表。心得对应 inspiration 表记录。

#### 3.4.6 reviews 表

```sql
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE,
    content TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    create_time INTEGER NOT NULL,
    update_time INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### 3.4.7 ratings 表

```sql
CREATE TABLE ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    create_time INTEGER NOT NULL,
    update_time INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 3.5 meta.xml 元数据

```xml
<?xml version="1.0" encoding="UTF-8"?>
<meta>
  <version>1.1</version>
  <encryption>AES-256</encryption>
  <encrypt_scope>7</encrypt_scope>
</meta>
```

- version：协议版本（本规范必须为 "1.1"）。
- encryption：加密算法（推荐使用 AES-256）。
- encrypt_scope：整数（0-7，7 表示除 meta.xml 外的完全加密；取值 1-3 保留未定义）。共享批注功能要求该值为 0（见 5.4 节）。
- meta.xml 在任何 encrypt_scope 取值下都必须保持未加密（见 4.1 节）。

---

## 4. 加密与压缩

### 4.1 加密机制

- 目标：resources/、read_data.db 或整个文件。
- 算法：AES-256（默认）。推荐使用 GCM 模式以获得密文完整性校验；若使用 CBC 模式，必须附加 HMAC 进行完整性保护。
- 范围（encrypt_scope）：
  - 0：无加密
  - 1-3：保留，未定义；实现遇到这些取值时应当拒绝解析并报错
  - 4：仅 resources/
  - 5：resources/ 和 book_data/
  - 6：resources/ 和 read_data.db
  - 7：除 meta.xml 外的全部内容（meta.xml 必须始终保持未加密，否则实现无法读取加密参数）
- 密钥：推荐通过 PBKDF2（HMAC-SHA-256，迭代次数不少于 100,000，使用随机盐）从用户密码派生。盐和每次加密生成的 IV 必须随密文一同存储。
- 顺序：必须先加密目标内容，再进行 ZIP 压缩（已加密数据无法被有效压缩）。

### 4.2 压缩机制

- 目标：整个 .ex5 文件。
- 算法：ZIP（使用 DEFLATE）。
- 要求：实现必须使用 ZIP 压缩。

---

## 5. 远程同步协议

### 5.1 同步概览

- 目标：在多个设备间同步 read_data.db。
- 方法：基于时间戳的增量更新。

### 5.2 RESTful API 定义

#### 5.2.1 GET /sync/read_data

- 参数：
  - user_id：字符串（对应 users 表的 identifier 字段）
  - last_sync_time：整数（Unix 时间戳）
- 响应：
  
```json
{
  "status": "success",
  "data": {
    "users": 数组,
    "history": 数组,
    "records": 数组,
    "notes": 数组,
    "inspiration": 数组,
    "reviews": 数组,
    "ratings": 数组
  },
  "timestamp": 整数
}
```

备注：对于未加密文件，响应应当包含本书所有用户的 notes、inspiration、reviews 和 ratings（共享读取，见 5.4 节）；history 和 records 等私人阅读数据仍只返回请求用户自己的部分。

#### 5.2.2 POST /sync/read_data

- 请求体：

```json
{
  "user_id": 字符串 (对应 users 表的 identifier 字段),
  "last_sync_time": 整数,
  "data": 对象（匹配 read_data.db 表结构）
}
```

- 响应：
  
```json
{
  "status": "success",
  "timestamp": 整数
}
```

备注：服务端必须只应用属于请求用户（user_id）记录的变更；对其他用户记录的修改或删除必须拒绝（见 5.4 节）。

### 5.3 冲突解决

- 策略：基于 update_time 或 create_time 的最后写入获胜；时间戳相同时，以记录 id 较大者获胜。
- 可选：用户手动解决冲突。

### 5.4 共享批注与权限

批注、摘抄、心得、划线、评价和评分是针对本书的内容，天然随 .ex5 文件共享。规则如下：

- **前提条件**：仅当 meta.xml 中 encrypt_scope 为 0（未加密）时，共享生效；文件加密时实现必须只展示当前用户自己的数据。
- **共享读取**：未加密文件中，实现必须允许任何用户读取 read_data.db 内所有用户的 notes、inspiration、reviews 和 ratings；展示时应当通过 user_id 关联 users 表显示作者名称。
- **编辑权限**：仅原作者可以修改或删除自己的记录。实现必须通过当前登录用户的 identifier 与记录所属 users.identifier 匹配来判定作者身份，并拒绝对他人记录的一切编辑操作；服务端在 5.2.2 中同样强制该校验。
- **多用户合并**：同一本书的文件副本在用户间流转或经服务器合并时，用户按 users.identifier 匹配，记录按 uuid 匹配；uuid 相同但内容不同的记录按 update_time 最后写入获胜。本地自增 id 仅库内有效，合并时应当重新分配。
- **私人数据**：history 和 records 属于个人阅读行为数据，不参与共享展示，仅用于本人多设备同步。

---

## 6. 实现指南

### 6.1 解析和写入 .ex5 文件

实现必须：

- 提取 ZIP 存档。
- 解析 JSON 和 XML 文件。
- 访问 SQLite 数据库并验证模式。
- 按指定方式处理加密。
- 对他人（identifier 与当前用户不一致）的批注、心得、评价、评分记录只读展示，不提供编辑入口。

### 6.2 示例实现

Python 示例（读取笔记）：

```python
import zipfile, sqlite3
with zipfile.ZipFile('book.ex5', 'r') as z:
    z.extract('read_data.db', 'temp/')
conn = sqlite3.connect('temp/read_data.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM notes")
notes = cursor.fetchall()
conn.close()
```

---

## 7. 安全考虑

- 加密：使用强密钥和安全密钥管理；不得将密钥或用户密码明文写入 .ex5 文件。
- 同步：API 调用使用 HTTPS。
- 数据验证：验证所有输入以防注入攻击。
- 解压安全：实现应当限制解压后的总大小和文件数量，以防范 ZIP 炸弹攻击。
- 共享隐私：未加密文件中的所有批注、心得、评价和评分对任何持有该文件的人可见；实现应当在用户创建这些内容时给出明确提示。需要隐私时应启用加密。
- 身份校验：服务端必须通过认证令牌校验请求者身份，防止伪造 identifier 冒充他人发布或篡改内容。

---

## 8. IANA 考虑

本文档目前无需 IANA 操作。

## 9. 参考文献

- RFC 2119：RFC 中用于指示要求级别的关键词
- SQLite 文档：<https://sqlite.org/>
- ZIP 文件格式：<https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT>

## 10. 致谢

感谢 EX5 团队提供的反馈和灵感。
