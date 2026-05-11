import json
import os
import sqlite3

from models import AIAnalysis, Attachment, Notice


class DBManager:
    def __init__(self, db_path: str = "data/notices.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                publish_time TEXT,
                department TEXT,
                raw_text TEXT,
                content TEXT,
                attachments TEXT,
                ai_analysis TEXT
            )
        """)
        cursor.execute("PRAGMA table_info(notices)")
        columns = {row[1] for row in cursor.fetchall()}
        if "attachments" not in columns:
            cursor.execute("ALTER TABLE notices ADD COLUMN attachments TEXT")
        if "ai_analysis" not in columns:
            cursor.execute("ALTER TABLE notices ADD COLUMN ai_analysis TEXT")
        self.conn.commit()

    def exists(self, url: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM notices WHERE url = ?", (url,))
        return cursor.fetchone() is not None

    def get_by_url(self, url: str) -> Notice | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT title, url, publish_time, department, raw_text, content, attachments, ai_analysis FROM notices WHERE url = ?",
            (url,),
        )
        row = cursor.fetchone()
        return self._row_to_notice(row) if row else None

    def insert(self, notice: Notice):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO notices (url, title, publish_time, department, raw_text, content, attachments, ai_analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notice.url,
                notice.title,
                notice.publish_time,
                notice.department,
                notice.raw_text,
                notice.content,
                json.dumps([attachment.__dict__ for attachment in notice.attachments], ensure_ascii=False),
                json.dumps(notice.ai_analysis.__dict__, ensure_ascii=False) if notice.ai_analysis else None,
            ))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass

    def get_all(self) -> list[Notice]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, url, publish_time, department, raw_text, content, attachments, ai_analysis FROM notices ORDER BY id DESC")
        rows = cursor.fetchall()
        return [self._row_to_notice(row) for row in rows]

    def get_by_publish_date(self, publish_date: str) -> list[Notice]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT title, url, publish_time, department, raw_text, content, attachments, ai_analysis
            FROM notices
            WHERE publish_time = ?
            ORDER BY id DESC
            """,
            (publish_date,),
        )
        rows = cursor.fetchall()
        return [self._row_to_notice(row) for row in rows]

    def _row_to_notice(self, row) -> Notice:
        return Notice(
            title=row[0],
            url=row[1],
            publish_time=row[2],
            department=row[3],
            raw_text=row[4],
            content=row[5],
            attachments=[
                Attachment(name=item.get("name", ""), url=item.get("url", ""))
                for item in json.loads(row[6] or "[]")
            ],
            ai_analysis=AIAnalysis(**json.loads(row[7])) if row[7] else None,
        )

    def close(self):
        self.conn.close()
