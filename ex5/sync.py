"""Server-side helpers for the remote synchronization protocol (spec 5.2).

build_get_response implements GET /sync/read_data (5.2.1): shared tables
return ALL users' rows (shared reading, 5.4); private tables return only
the requesting user's rows.

apply_post implements POST /sync/read_data (5.2.2) with the mandatory
permission check (5.2.2 note / 5.4 edit permission): only rows authored
by the requesting user are applied; anything else raises PermissionDenied.
"""

import sqlite3
import time

from . import schema
from .core import PermissionDenied, ValidationError


def _now():
    return int(time.time())


def _user_id(conn, identifier):
    row = conn.execute(
        "SELECT id FROM users WHERE identifier = ?", (identifier,)
    ).fetchone()
    if not row:
        raise ValidationError(f"unknown user identifier: {identifier!r}")
    return row["id"]


def _rows(conn, sql, params):
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(sql, params)]


def build_get_response(conn, user_identifier, last_sync_time=0):
    """Build the response body for GET /sync/read_data (spec 5.2.1)."""
    uid = _user_id(conn, user_identifier)
    data = {}
    # users: all rows are needed so clients can display author names (5.4).
    data["users"] = _rows(conn, "SELECT * FROM users", ())
    # shared tables: every user's rows (shared reading).
    for table in schema.SHARED_TABLES:
        data[table] = _rows(
            conn,
            f"SELECT * FROM {table} "
            f"WHERE COALESCE(update_time, create_time) > ?",
            (last_sync_time,),
        )
    # private tables: only the requester's rows.
    data["history"] = _rows(
        conn,
        "SELECT * FROM history WHERE user_id = ? AND start_time > ?",
        (uid, last_sync_time),
    )
    data["records"] = _rows(
        conn,
        "SELECT * FROM records WHERE user_id = ? AND record_time > ?",
        (uid, last_sync_time),
    )
    return {"status": "success", "data": data, "timestamp": _now()}


def apply_post(conn, user_identifier, data):
    """Apply a POST /sync/read_data body (spec 5.2.2).

    Every shared-table row must carry an 'identifier' field naming its
    author; rows not authored by user_identifier are rejected. Shared rows
    are upserted by uuid with last-write-wins on update_time. Private
    tables are upserted by id and forcibly attributed to the requester.
    """
    uid = _user_id(conn, user_identifier)
    rejected = []

    for table in schema.SHARED_TABLES:
        fields = schema.SHARED_TABLE_FIELDS[table]
        for row in data.get(table, []):
            author = row.get("identifier")
            if author != user_identifier:
                rejected.append({"table": table, "uuid": row.get("uuid"),
                                 "author": author})
                continue
            if not row.get("uuid"):
                continue
            existing = conn.execute(
                f"SELECT update_time, create_time FROM {table} WHERE uuid = ?",
                (row["uuid"],),
            ).fetchone()
            values = {k: row.get(k) for k in fields if k != "user_id"}
            values["user_id"] = uid
            if existing is None:
                cols = list(values)
                conn.execute(
                    f"INSERT INTO {table} ({', '.join(cols)}) "
                    f"VALUES ({', '.join('?' for _ in cols)})",
                    [values[c] for c in cols],
                )
            else:
                local_ts = (existing["update_time"]
                            or existing["create_time"] or 0)
                src_ts = row.get("update_time") or row.get("create_time") or 0
                if src_ts > local_ts:
                    cols = [c for c in values if c not in ("uuid", "create_time")]
                    conn.execute(
                        f"UPDATE {table} SET "
                        f"{', '.join(c + ' = ?' for c in cols)} WHERE uuid = ?",
                        [values[c] for c in cols] + [row["uuid"]],
                    )

    for table in schema.PRIVATE_TABLES:
        for row in data.get(table, []):
            if "id" not in row:
                continue
            cols = [k for k in row if k != "user_id"]
            values = [row[c] for c in cols] + [uid]
            conn.execute(
                f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}, user_id) "
                f"VALUES ({', '.join('?' for _ in cols)}, ?)",
                values,
            )

    conn.commit()
    if rejected:
        raise PermissionDenied(
            f"rejected {len(rejected)} row(s) not authored by "
            f"{user_identifier!r} (spec 5.2.2 note): {rejected}"
        )
    return {"status": "success", "timestamp": _now()}
