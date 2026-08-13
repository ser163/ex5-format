"""Unit tests for the ex5 reference implementation (spec v1.1)."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ex5 import (Ex5, ValidationError, EncryptionNotSupported,
                 PermissionDenied)
from ex5 import sync


BOOK_INFO = {
    "title": "Sample Book",
    "authors": ["Author A"],
    "pub_date": 1609459200,
    "version": "1.0",
    "cover_id": 0,
    "chapter_count": 2,
    "word_count": 12345,
}
CHAPTERS = [
    {"index": 1, "title": "Chapter 1", "resource_ids": [901]},
    {"index": 2, "title": "Chapter 2", "resource_ids": [902]},
]
RESOURCES = [
    {"resource_id": 0, "content": "cover.png", "type": "image",
     "resType": "png"},
    {"resource_id": 901, "content": "chapter1.txt", "type": "txt"},
    {"resource_id": 902, "content": "chapter2.txt", "type": "txt"},
]
RESOURCE_FILES = {
    "cover.png": b"\x89PNG fake",
    "chapter1.txt": "第一章内容".encode("utf-8"),
    "chapter2.txt": "第二章内容".encode("utf-8"),
}


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ex5test_")
        self.path = os.path.join(self.dir, "book.ex5")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def create_book(self, path=None):
        return Ex5.create(path or self.path, BOOK_INFO, CHAPTERS, RESOURCES,
                          RESOURCE_FILES)


class TestCreateRead(Base):
    def test_roundtrip(self):
        book = self.create_book()
        book.close()
        with Ex5(self.path) as book:
            self.assertEqual(book.meta["version"], "1.1")
            self.assertEqual(book.meta["encrypt_scope"], 0)
            self.assertEqual(book.info["title"], "Sample Book")
            self.assertEqual(len(book.chapters), 2)
            self.assertEqual(book.read_resource("chapter1.txt"),
                             "第一章内容".encode("utf-8"))

    def test_reserved_resource_id_rejected(self):
        bad = [{"resource_id": 500, "content": "x.txt", "type": "txt"}]
        with self.assertRaises(ValidationError):
            Ex5.create(self.path, BOOK_INFO, CHAPTERS, bad)

    def test_content_resource_id_accepted(self):
        self.create_book()  # 901/902 are valid content ids; no exception

    def test_invalid_info_rejected(self):
        with self.assertRaises(ValidationError):
            Ex5.create(self.path, {"authors": ["A"]})

    def test_encrypted_file_rejected(self):
        import zipfile
        self.create_book().close()
        # rewrite meta.xml with encrypt_scope=6
        tmp = self.path + ".tmp"
        with zipfile.ZipFile(self.path) as zin, \
                zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "meta.xml":
                    data = (b'<?xml version="1.0" encoding="UTF-8"?><meta>'
                            b'<version>1.1</version><encryption>AES-256'
                            b'</encryption><encrypt_scope>6</encrypt_scope>'
                            b'</meta>')
                zout.writestr(item, data)
        os.replace(tmp, self.path)
        with self.assertRaises(EncryptionNotSupported):
            Ex5(self.path)


class TestSharingPermissions(Base):
    def setUp(self):
        super().setUp()
        self.book = self.create_book()
        self.book.add_user("alice@example.com", name="Alice")
        self.book.add_user("bob@example.com", name="Bob")

    def tearDown(self):
        self.book.close()
        super().tearDown()

    def test_shared_reading_all_users(self):
        self.book.add_note("alice@example.com", content="alice 的批注")
        self.book.add_review("bob@example.com", content="bob 的评价")
        self.book.add_rating("bob@example.com", 4)

        notes = self.book.annotations("notes", current_user="bob@example.com")
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["author_name"], "Alice")
        self.assertFalse(notes[0]["editable"])  # not bob's own note

        notes = self.book.annotations("notes", current_user="alice@example.com")
        self.assertTrue(notes[0]["editable"])

        self.assertEqual(len(self.book.annotations("reviews")), 1)
        self.assertEqual(len(self.book.annotations("ratings")), 1)

    def test_author_only_edit(self):
        uuid = self.book.add_note("alice@example.com", content="原文")
        self.book.update_shared("notes", uuid, "alice@example.com",
                                content="作者修改")
        with self.assertRaises(PermissionDenied):
            self.book.update_shared("notes", uuid, "bob@example.com",
                                    content="他人篡改")
        with self.assertRaises(PermissionDenied):
            self.book.delete_shared("notes", uuid, "bob@example.com")
        self.book.delete_shared("notes", uuid, "alice@example.com")
        self.assertEqual(self.book.annotations("notes"), [])

    def test_excerpt_and_highlight_mapping(self):
        # 摘抄: original + range; 划线: range only (spec 3.4.4 mapping)
        excerpt = self.book.add_note("alice@example.com", content="我的摘抄",
                                     range_start=10, range_end=20,
                                     original="原文片段")
        highlight = self.book.add_note("alice@example.com",
                                       range_start=30, range_end=40)
        rows = {r["uuid"]: r for r in self.book.annotations("notes")}
        self.assertEqual(rows[excerpt]["original"], "原文片段")
        self.assertIsNone(rows[highlight]["content"])

    def test_rating_range(self):
        with self.assertRaises(ValidationError):
            self.book.add_rating("alice@example.com", 6)


class TestMerge(Base):
    def test_multi_user_merge(self):
        book = self.create_book()
        book.add_user("alice@example.com", name="Alice")
        book.add_user("bob@example.com", name="Bob")
        book.add_note("alice@example.com", content="v1")
        book.save()
        book.close()

        # two copies diverge from the common origin
        copy2 = os.path.join(self.dir, "copy2.ex5")
        shutil.copy(self.path, copy2)

        with Ex5(self.path) as b1:
            u_alice = b1.annotations("notes")[0]["uuid"]
            b1.update_shared("notes", u_alice, "alice@example.com",
                             content="v2-newer")
            # make b1's version clearly newer
            b1.conn.execute("UPDATE notes SET update_time = 2000 "
                            "WHERE uuid = ?", (u_alice,))
            b1.conn.commit()
            b1.save()

        with Ex5(copy2) as b2:
            b2.add_note("bob@example.com", content="bob 的心得划线")
            u_alice2 = b2.annotations("notes")[0]["uuid"]
            b2.update_shared("notes", u_alice2, "alice@example.com",
                             content="v2-older")
            b2.conn.execute("UPDATE notes SET update_time = 1000 "
                            "WHERE uuid = ?", (u_alice2,))
            b2.conn.commit()
            b2.save()

        with Ex5(self.path) as b1:
            stats = b1.merge(copy2)
            notes = b1.annotations("notes")
            authors = {n["author_identifier"] for n in notes}
            self.assertEqual(authors, {"alice@example.com", "bob@example.com"})
            # LWW: the newer version (update_time 2000) wins
            alice_note = [n for n in notes
                          if n["author_identifier"] == "alice@example.com"][0]
            self.assertEqual(alice_note["content"], "v2-newer")
            self.assertEqual(stats["inserted"], 1)
            self.assertEqual(stats["kept"], 1)
            b1.save()


class TestSync(Base):
    def setUp(self):
        super().setUp()
        self.book = self.create_book()
        self.book.add_user("alice@example.com", name="Alice")
        self.book.add_user("bob@example.com", name="Bob")

    def tearDown(self):
        self.book.close()
        super().tearDown()

    def test_get_response_shares_annotations_hides_private(self):
        self.book.add_note("alice@example.com", content="共享批注")
        conn = self.book.conn
        conn.execute(
            "INSERT INTO history (user_id, start_time) VALUES (1, 100)")
        conn.commit()
        resp = sync.build_get_response(conn, "bob@example.com")
        # shared tables visible to bob
        self.assertEqual(len(resp["data"]["notes"]), 1)
        self.assertEqual(len(resp["data"]["users"]), 2)
        # private history of alice NOT visible to bob
        self.assertEqual(resp["data"]["history"], [])

    def test_post_rejects_foreign_rows(self):
        conn = self.book.conn
        payload = {
            "notes": [
                {"uuid": "u-own", "identifier": "alice@example.com",
                 "content": "自己的", "type": "txt", "create_time": 100},
                {"uuid": "u-foreign", "identifier": "bob@example.com",
                 "content": "冒充他人", "type": "txt", "create_time": 100},
            ]
        }
        with self.assertRaises(PermissionDenied):
            sync.apply_post(conn, "alice@example.com", payload)
        # own row applied, foreign row not
        notes = self.book.annotations("notes")
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["uuid"], "u-own")


if __name__ == "__main__":
    unittest.main(verbosity=2)
