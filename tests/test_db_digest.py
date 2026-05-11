import tempfile
import unittest
from pathlib import Path

from db import DBManager
from models import Notice


class NoticeDatabaseDigestTests(unittest.TestCase):
    def test_get_by_publish_date_returns_matching_notices(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = DBManager(str(Path(temp_dir) / "notices.db"))
            db.insert(Notice(title="今天通知", url="https://example.com/today", publish_time="2026-05-11"))
            db.insert(Notice(title="昨天通知", url="https://example.com/yesterday", publish_time="2026-05-10"))

            notices = db.get_by_publish_date("2026-05-11")
            db.close()

        self.assertEqual([notice.title for notice in notices], ["今天通知"])


if __name__ == "__main__":
    unittest.main()
