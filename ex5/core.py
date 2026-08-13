"""Core reader/writer for the .ex5 file format, spec version 1.1.

Implements container creation/opening, book_data access, multi-user
annotation CRUD with author-only edit permission (spec 5.4), and
multi-user merge (identifier + uuid, last-write-wins).

Encryption is NOT implemented in this reference implementation: only
unencrypted files (encrypt_scope = 0) can be created or opened.
"""

import json
import os
import shutil
import sqlite3
import tempfile
import time
import uuid as uuidlib
import zipfile
from xml.etree import ElementTree as ET

from . import schema

SPEC_VERSION = "1.1"

# Resource ID ranges (spec 3.2.3 constraints).
COVER_ID_MAX = 100
RESERVED_ID_RANGE = range(101, 901)
CONTENT_ID_MIN = 901
CONTENT_ID_MAX = 1001000


class Ex5Error(Exception):
    """Base error for the ex5 package."""


class ValidationError(Ex5Error):
    """Input data violates the specification."""


class EncryptionNotSupported(Ex5Error):
    """Encrypted files are not supported by this reference implementation."""


class PermissionDenied(Ex5Error, PermissionError):
    """A user attempted to edit or delete another user's record (spec 5.4)."""


def _now():
    return int(time.time())


def _meta_xml(encrypt_scope):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<meta>\n'
        f'  <version>{SPEC_VERSION}</version>\n'
        '  <encryption>AES-256</encryption>\n'
        f'  <encrypt_scope>{encrypt_scope}</encrypt_scope>\n'
        '</meta>\n'
    )


def _validate_resources(resources):
    """Validate resources.json entries against the ID ranges in spec 3.2.3."""
    for res in resources:
        rid = res.get("resource_id")
        if not isinstance(rid, int) or rid < 0 or rid > CONTENT_ID_MAX:
            raise ValidationError(f"invalid resource_id: {rid!r}")
        if rid in RESERVED_ID_RANGE:
            raise ValidationError(
                f"resource_id {rid} falls in the reserved range 101-900 "
                "(spec 3.2.3)"
            )
        rtype = res.get("type")
        if rtype not in schema.CONTENT_TYPES:
            raise ValidationError(f"invalid resource type: {rtype!r}")


def _validate_info(info):
    if not isinstance(info.get("title"), str):
        raise ValidationError("info.json requires a string 'title'")
    authors = info.get("authors")
    if not isinstance(authors, list) or not all(isinstance(a, str) for a in authors):
        raise ValidationError("info.json requires a list 'authors' of strings")
    cover_id = info.get("cover_id")
    if cover_id is not None and not (0 <= cover_id <= COVER_ID_MAX):
        raise ValidationError("cover_id must be within 0-100 (spec 3.2.1)")


class Ex5:
    """An opened .ex5 file. Use Ex5.create() for new files."""

    def __init__(self, path):
        self.path = path
        self._tmpdir = tempfile.mkdtemp(prefix="ex5_")
        self._db_path = os.path.join(self._tmpdir, "read_data.db")
        with zipfile.ZipFile(path, "r") as z:
            names = set(z.namelist())
            if "meta.xml" not in names:
                raise ValidationError("meta.xml missing (spec 3.5)")
            self.meta = self._parse_meta(z.read("meta.xml"))
            if self.meta["encrypt_scope"] != 0:
                raise EncryptionNotSupported(
                    f"encrypt_scope={self.meta['encrypt_scope']}: this reference "
                    "implementation only supports unencrypted files"
                )
            if "book_data/info.json" not in names:
                raise ValidationError("book_data/info.json missing (spec 3.2.1)")
            self._info = json.loads(z.read("book_data/info.json").decode("utf-8"))
            self._chapters = (
                json.loads(z.read("book_data/chapters.json").decode("utf-8"))
                if "book_data/chapters.json" in names else []
            )
            self._resources = (
                json.loads(z.read("book_data/resources.json").decode("utf-8"))
                if "book_data/resources.json" in names else []
            )
            if "read_data.db" in names:
                with open(self._db_path, "wb") as f:
                    f.write(z.read("read_data.db"))
        self.conn = sqlite3.connect(self._db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        schema.init_db(self.conn)

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    @classmethod
    def create(cls, path, info, chapters=None, resources=None,
               resource_files=None):
        """Create a new unencrypted .ex5 file.

        resource_files: dict mapping filename -> bytes or a local file path,
        written under resources/ (spec 3.3).
        """
        chapters = chapters or []
        resources = resources or []
        resource_files = resource_files or {}
        _validate_info(info)
        _validate_resources(resources)

        tmpdir = tempfile.mkdtemp(prefix="ex5_create_")
        try:
            db_path = os.path.join(tmpdir, "read_data.db")
            conn = sqlite3.connect(db_path)
            schema.init_db(conn)
            conn.close()

            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("book_data/info.json",
                           json.dumps(info, ensure_ascii=False, indent=2))
                z.writestr("book_data/chapters.json",
                           json.dumps(chapters, ensure_ascii=False, indent=2))
                z.writestr("book_data/resources.json",
                           json.dumps(resources, ensure_ascii=False, indent=2))
                for filename, content in resource_files.items():
                    if isinstance(content, (str, os.PathLike)):
                        z.write(content, f"resources/{filename}")
                    else:
                        z.writestr(f"resources/{filename}", content)
                z.write(db_path, "read_data.db")
                z.writestr("meta.xml", _meta_xml(encrypt_scope=0))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        return cls(path)

    @staticmethod
    def _parse_meta(data):
        root = ET.fromstring(data.decode("utf-8"))
        def text(tag, default=None):
            el = root.find(tag)
            return el.text.strip() if el is not None and el.text else default
        return {
            "version": text("version"),
            "encryption": text("encryption"),
            "encrypt_scope": int(text("encrypt_scope", "0")),
        }

    # ------------------------------------------------------------------
    # metadata access
    # ------------------------------------------------------------------
    @property
    def info(self):
        return self._info

    @property
    def chapters(self):
        return self._chapters

    @property
    def resources(self):
        return self._resources

    def read_resource(self, filename):
        """Read a file from resources/ (spec 3.3)."""
        with zipfile.ZipFile(self.path, "r") as z:
            return z.read(f"resources/{filename}")

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    def add_user(self, identifier, name=None, gender=None, birth_date=None):
        """Add a user; returns the user id. Idempotent on identifier."""
        row = self.conn.execute(
            "SELECT id FROM users WHERE identifier = ?", (identifier,)
        ).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
            "INSERT INTO users (identifier, name, gender, birth_date) "
            "VALUES (?, ?, ?, ?)",
            (identifier, name, gender, birth_date),
        )
        self.conn.commit()
        return cur.lastrowid

    def _user_id(self, identifier):
        row = self.conn.execute(
            "SELECT id FROM users WHERE identifier = ?", (identifier,)
        ).fetchone()
        if not row:
            raise ValidationError(f"unknown user identifier: {identifier!r}")
        return row["id"]

    def users(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM users")]

    # ------------------------------------------------------------------
    # shared annotations (spec 5.4)
    # ------------------------------------------------------------------
    def _add_shared(self, table, user_identifier, **fields):
        if table not in schema.SHARED_TABLES:
            raise ValidationError(f"not a shared table: {table}")
        if "type" in schema.SHARED_TABLE_FIELDS[table] and "type" in fields:
            if fields["type"] not in schema.CONTENT_TYPES:
                raise ValidationError(f"invalid type: {fields['type']!r}")
        record_uuid = fields.pop("uuid", None) or str(uuidlib.uuid4())
        user_id = self._user_id(user_identifier)
        now = _now()
        columns = ["uuid", "user_id", "create_time"]
        values = [record_uuid, user_id, now]
        for key, value in fields.items():
            if key not in schema.SHARED_TABLE_FIELDS[table]:
                raise ValidationError(f"unknown field for {table}: {key}")
            if key in ("uuid", "user_id", "create_time"):
                continue
            columns.append(key)
            values.append(value)
        placeholders = ", ".join("?" for _ in columns)
        self.conn.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )
        self.conn.commit()
        return record_uuid

    def add_note(self, user_identifier, content=None, type="txt",
                 chapter_id=None, history_id=None, records_id=None,
                 range_start=None, range_end=None, original=None):
        """Add a note/excerpt/highlight (mapping per spec 3.4.4)."""
        return self._add_shared(
            "notes", user_identifier, content=content, type=type,
            chapter_id=chapter_id, history_id=history_id,
            records_id=records_id, range_start=range_start,
            range_end=range_end, original=original,
        )

    def add_inspiration(self, user_identifier, content=None, type="txt",
                        chapter_id=None, history_id=None, records_id=None):
        return self._add_shared(
            "inspiration", user_identifier, content=content, type=type,
            chapter_id=chapter_id, history_id=history_id,
            records_id=records_id,
        )

    def add_review(self, user_identifier, content):
        return self._add_shared("reviews", user_identifier, content=content)

    def add_rating(self, user_identifier, rating):
        if not (1 <= rating <= 5):
            raise ValidationError("rating must be within 1-5 (spec 3.4.7)")
        return self._add_shared("ratings", user_identifier, rating=rating)

    def annotations(self, table, current_user=None):
        """Read shared records of ALL users (spec 5.4, shared reading).

        Each row is a dict joined with author info; when current_user is
        given, an 'editable' flag is added (True only for the author's own
        rows).
        """
        if table not in schema.SHARED_TABLES:
            raise ValidationError(f"not a shared table: {table}")
        rows = self.conn.execute(
            f"SELECT t.*, u.identifier AS author_identifier, "
            f"u.name AS author_name FROM {table} t "
            f"JOIN users u ON u.id = t.user_id "
            f"ORDER BY t.create_time, t.id"
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            if current_user is not None:
                item["editable"] = (item["author_identifier"] == current_user)
            result.append(item)
        return result

    def _check_author(self, table, record_uuid, current_user):
        row = self.conn.execute(
            f"SELECT u.identifier FROM {table} t "
            f"JOIN users u ON u.id = t.user_id WHERE t.uuid = ?",
            (record_uuid,),
        ).fetchone()
        if not row:
            raise ValidationError(f"no {table} record with uuid {record_uuid!r}")
        if row["identifier"] != current_user:
            raise PermissionDenied(
                f"user {current_user!r} may not edit a record authored by "
                f"{row['identifier']!r} (spec 5.4, edit permission)"
            )

    def update_shared(self, table, record_uuid, current_user, **fields):
        """Update a shared record; only the original author may do so."""
        if table not in schema.SHARED_TABLES:
            raise ValidationError(f"not a shared table: {table}")
        self._check_author(table, record_uuid, current_user)
        allowed = set(schema.SHARED_TABLE_FIELDS[table]) - {
            "uuid", "user_id", "create_time"}
        updates, values = [], []
        for key, value in fields.items():
            if key not in allowed:
                raise ValidationError(f"field {key} is not updatable on {table}")
            updates.append(f"{key} = ?")
            values.append(value)
        updates.append("update_time = ?")
        values.append(_now())
        values.append(record_uuid)
        self.conn.execute(
            f"UPDATE {table} SET {', '.join(updates)} WHERE uuid = ?", values)
        self.conn.commit()

    def delete_shared(self, table, record_uuid, current_user):
        """Delete a shared record; only the original author may do so."""
        if table not in schema.SHARED_TABLES:
            raise ValidationError(f"not a shared table: {table}")
        self._check_author(table, record_uuid, current_user)
        self.conn.execute(f"DELETE FROM {table} WHERE uuid = ?", (record_uuid,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # multi-user merge (spec 5.4)
    # ------------------------------------------------------------------
    def merge(self, other_path):
        """Merge another copy of this book into the current file.

        Users are matched by users.identifier, records by uuid;
        conflicting rows resolve by last-write-wins on update_time
        (fallback create_time). Local autoincrement ids are reassigned.
        Private tables (history/records) are NOT merged; references to
        them in imported rows are cleared.
        """
        stats = {"users_added": 0, "inserted": 0, "updated": 0, "kept": 0}
        with Ex5(other_path) as other:
            user_map = {}
            for row in other.conn.execute("SELECT * FROM users"):
                local = self.conn.execute(
                    "SELECT id FROM users WHERE identifier = ?",
                    (row["identifier"],),
                ).fetchone()
                if local:
                    user_map[row["id"]] = local["id"]
                else:
                    cur = self.conn.execute(
                        "INSERT INTO users (identifier, name, gender, "
                        "birth_date, lock, cipher) VALUES (?, ?, ?, ?, ?, ?)",
                        (row["identifier"], row["name"], row["gender"],
                         row["birth_date"], row["lock"], row["cipher"]),
                    )
                    user_map[row["id"]] = cur.lastrowid
                    stats["users_added"] += 1

            for table in schema.SHARED_TABLES:
                fields = schema.SHARED_TABLE_FIELDS[table]
                for row in other.conn.execute(f"SELECT * FROM {table}"):
                    src = dict(row)
                    if not src.get("uuid"):
                        continue
                    src["user_id"] = user_map[src["user_id"]]
                    # references to private tables do not survive a merge
                    for ref in ("history_id", "records_id"):
                        if ref in src:
                            src[ref] = None
                    local = self.conn.execute(
                        f"SELECT * FROM {table} WHERE uuid = ?",
                        (src["uuid"],),
                    ).fetchone()
                    src_ts = src.get("update_time") or src.get("create_time") or 0
                    if local is None:
                        cols = [f for f in fields]
                        self.conn.execute(
                            f"INSERT INTO {table} ({', '.join(cols)}) "
                            f"VALUES ({', '.join('?' for _ in cols)})",
                            [src.get(c) for c in cols],
                        )
                        stats["inserted"] += 1
                    else:
                        local_ts = (local["update_time"]
                                    or local["create_time"] or 0)
                        if src_ts > local_ts:
                            cols = [f for f in fields
                                    if f not in ("uuid", "create_time")]
                            self.conn.execute(
                                f"UPDATE {table} SET "
                                f"{', '.join(c + ' = ?' for c in cols)} "
                                f"WHERE uuid = ?",
                                [src.get(c) for c in cols] + [src["uuid"]],
                            )
                            stats["updated"] += 1
                        else:
                            stats["kept"] += 1
            self.conn.commit()
        return stats

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def save(self):
        """Write the current read_data.db back into the .ex5 archive."""
        self.conn.commit()
        self.conn.close()
        tmp_path = self.path + ".tmp"
        with zipfile.ZipFile(self.path, "r") as zin, \
                zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "read_data.db":
                    continue
                zout.writestr(item, zin.read(item.filename))
            zout.write(self._db_path, "read_data.db")
        os.replace(tmp_path, self.path)
        self.conn = sqlite3.connect(self._db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self):
        try:
            self.conn.close()
        finally:
            shutil.rmtree(self._tmpdir, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False
