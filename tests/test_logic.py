import sys
import unittest
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server_code"))
import logic


class TestEmail(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(logic.normalize_email("  Hans@GMAIL.com "), "hans@gmail.com")

    def test_valid(self):
        self.assertTrue(logic.valid_email("a@b.no"))
        self.assertFalse(logic.valid_email("ikke-epost"))
        self.assertFalse(logic.valid_email("a@b"))
        self.assertFalse(logic.valid_email(""))
        self.assertFalse(logic.valid_email("a b@c.no"))


class TestRateLimit(unittest.TestCase):
    today = datetime.date(2026, 7, 24)

    def test_first_ever(self):
        self.assertEqual(logic.next_reg_count(None, 0, self.today), 1)

    def test_new_day_resets(self):
        yesterday = datetime.date(2026, 7, 23)
        self.assertEqual(logic.next_reg_count(yesterday, 3, self.today), 1)

    def test_increments_same_day(self):
        self.assertEqual(logic.next_reg_count(self.today, 1, self.today), 2)

    def test_limit_reached(self):
        self.assertIsNone(logic.next_reg_count(self.today, 3, self.today))


class TestToken(unittest.TestCase):
    def test_token_long_and_unique(self):
        a, b = logic.new_token(), logic.new_token()
        self.assertGreaterEqual(len(a), 20)
        self.assertNotEqual(a, b)


class TestBookmarklet(unittest.TestCase):
    def test_contents(self):
        js = logic.bookmarklet_js("TOKEN123")
        self.assertTrue(js.startswith("javascript:"))
        self.assertIn("TOKEN123", js)
        self.assertIn("https://send2me.app/_/api/sendlink", js)
        self.assertIn("encodeURIComponent(location.href)", js)
        self.assertIn("encodeURIComponent(document.title)", js)
        self.assertIn("window.open", js)
        self.assertIn("location.href=u", js)  # popup-blokkering-fallback


class TestTexts(unittest.TestCase):
    def test_email_text(self):
        txt = logic.registration_email_text("TOK", "javascript:x")
        self.assertIn("TOK", txt)
        self.assertIn("javascript:x", txt)
        self.assertIn("https://send2me.app", txt)

    def test_sent_page(self):
        html = logic.sent_page_html()
        self.assertIn("Sent", html)
        self.assertIn("window.close", html)
        self.assertIn("history.back", html)

    def test_error_page(self):
        self.assertIn("Unknown", logic.error_page_html("Unknown key"))


if __name__ == "__main__":
    unittest.main()
