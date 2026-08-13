"""ex5-format v1.1 database schema definitions.

Matches Section 3.4 of the EX5-001 specification (version 1.1).
"""

# Tables whose rows are shared across all users of an unencrypted file
# (spec 5.4): notes (批注/摘抄/划线), inspiration (心得),
# reviews (评价), ratings (评分).
SHARED_TABLES = ("notes", "inspiration", "reviews", "ratings")

# Personal reading-behavior data; never shared (spec 5.4, "Private data").
PRIVATE_TABLES = ("history", "records")

# Valid resource / content types (spec 3.2.3 and CHECK constraints).
CONTENT_TYPES = ("txt", "image", "html", "video", "sound", "binary")

# Updatable fields per shared table (uuid and user_id are immutable).
SHARED_TABLE_FIELDS = {
    "notes": (
        "uuid", "content", "type", "create_time", "update_time", "user_id",
        "chapter_id", "history_id", "records_id", "range_start", "range_end",
        "original",
    ),
    "inspiration": (
        "uuid", "type", "content", "create_time", "update_time", "user_id",
        "chapter_id", "history_id", "records_id",
    ),
    "reviews": ("uuid", "content", "user_id", "create_time", "update_time"),
    "ratings": ("uuid", "user_id", "rating", "create_time", "update_time"),
}

DDL = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT NOT NULL UNIQUE,
        name TEXT,
        gender TEXT,
        birth_date INTEGER,
        lock INTEGER DEFAULT 0 CHECK (lock IN (0, 1)),
        cipher BLOB
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS history (
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
    """,
    """
    CREATE TABLE IF NOT EXISTS records (
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
    """,
    """
    CREATE TABLE IF NOT EXISTS notes (
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
    """,
    """
    CREATE TABLE IF NOT EXISTS inspiration (
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
    """,
    """
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT UNIQUE,
        content TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        create_time INTEGER NOT NULL,
        update_time INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT UNIQUE,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        create_time INTEGER NOT NULL,
        update_time INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,
)


def init_db(conn):
    """Create all v1.1 tables on an open sqlite3 connection."""
    for statement in DDL:
        conn.execute(statement)
    conn.commit()
