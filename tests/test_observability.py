import logging
import tempfile
import unittest
from pathlib import Path

from error_notifier import notify_error
from logger_setup import setup_logging


class LoggingSetupTests(unittest.TestCase):
    def test_setup_logging_writes_to_file(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            log_path = Path(temp_dir) / "notice_robot.log"

            logger = setup_logging(str(log_path), logger_name="test.notice_robot")
            logger.info("hello logging")
            for handler in logger.handlers:
                handler.flush()

            text = log_path.read_text(encoding="utf-8")

        self.assertIn("hello logging", text)
        self.assertIn("INFO", text)


class ErrorNotifierTests(unittest.TestCase):
    def test_notify_error_dry_run_logs_without_sending(self):
        sent = []
        logged = []

        def send_func(message):
            sent.append(message)
            return True

        class FakeLogger:
            def error(self, message):
                logged.append(message)

        result = notify_error(
            stage="飞书推送",
            error=RuntimeError("接口失败"),
            dry_run=True,
            send_func=send_func,
            logger=FakeLogger(),
        )

        self.assertFalse(result)
        self.assertEqual(sent, [])
        self.assertIn("飞书推送", logged[0])

    def test_notify_error_sends_alert_when_not_dry_run(self):
        sent = []

        def send_func(message):
            sent.append(message)
            return True

        result = notify_error(
            stage="整轮任务",
            error=RuntimeError("任务崩溃"),
            dry_run=False,
            send_func=send_func,
        )

        self.assertTrue(result)
        self.assertEqual(len(sent), 1)
        self.assertIn("通知机器人异常", sent[0])
        self.assertIn("整轮任务", sent[0])
        self.assertIn("任务崩溃", sent[0])
