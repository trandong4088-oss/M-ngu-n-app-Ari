"""
Unit tests for aro CLI entrypoint.
"""

import io
import unittest
from contextlib import redirect_stdout
from aro_worker import __version__
from aro_worker.cli import main


class TestCli(unittest.TestCase):
    def test_version_flag(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        output = buf.getvalue().strip()
        self.assertIn(f"aro-worker {__version__}", output)

    def test_help_flag(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        output = buf.getvalue()
        self.assertIn("doctor", output)
        self.assertIn("worker", output)

    def test_worker_subcommand_unimplemented_in_a01(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["worker"])
        self.assertEqual(ret, 1)
        output = buf.getvalue()
        self.assertIn("NOT_IMPLEMENTED in Task A01", output)
        self.assertIn("Task A04", output)


if __name__ == "__main__":
    unittest.main()
