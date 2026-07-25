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
        txt = logic.registration_email_text(
            "TOK", "javascript:x", "https://send2me.app/#?key=TOK")
        self.assertIn("TOK", txt)
        self.assertIn("javascript:x", txt)
        self.assertIn("https://send2me.app/#?key=TOK", txt)

    def test_sent_page(self):
        html = logic.sent_page_html()
        self.assertIn("Sent", html)
        self.assertIn("window.close", html)
        self.assertIn("history.back", html)
        self.assertIn("Saved", logic.sent_page_html("Saved"))

    def test_error_page(self):
        self.assertIn("Unknown", logic.error_page_html("Unknown key"))


class TestModeTags(unittest.TestCase):
    def test_mode(self):
        for m in ("email", "save", "both"):
            self.assertEqual(logic.normalize_mode(m), m)
        self.assertEqual(logic.normalize_mode(None), "both")
        self.assertEqual(logic.normalize_mode("junk"), "both")

    def test_tags(self):
        self.assertEqual(logic.normalize_tags(" a , b ,, "), "a, b")
        self.assertEqual(logic.normalize_tags(None), "")


class TestLinksPageUrl(unittest.TestCase):
    def test_url(self):
        self.assertEqual(logic.links_page_url("TOK"), "https://send2me.app/#?key=TOK")


class TestParseQuery(unittest.TestCase):
    def test_defaults(self):
        f, err = logic.parse_links_query({})
        self.assertIsNone(err)
        self.assertFalse(f["all"])
        self.assertFalse(f["keep"])
        self.assertIsNone(f["since"])
        self.assertIsNone(f["until"])
        self.assertIsNone(f["tag"])
        self.assertFalse(f["starred"])

    def test_flags_and_dates(self):
        f, err = logic.parse_links_query(
            {"all": "1", "keep": "True", "since": "2026-07-01",
             "until": "2026-07-25", "tag": "health", "starred": "yes"})
        self.assertIsNone(err)
        self.assertTrue(f["all"])
        self.assertTrue(f["keep"])
        self.assertEqual(f["since"], datetime.date(2026, 7, 1))
        self.assertEqual(f["until"], datetime.date(2026, 7, 25))
        self.assertEqual(f["tag"], "health")
        self.assertTrue(f["starred"])

    def test_bad_date(self):
        f, err = logic.parse_links_query({"since": "01.07.2026"})
        self.assertIsNone(f)
        self.assertIn("since", err)


class TestLinkMatches(unittest.TestCase):
    def link(self, **kw):
        base = {"saved": datetime.datetime(2026, 7, 20, 12, 0),
                "fetched_at": None, "tags": "health, econ", "starred": False}
        base.update(kw)
        return base

    def filters(self, **kw):
        f, _ = logic.parse_links_query(kw)
        return f

    def test_unfetched_default(self):
        self.assertTrue(logic.link_matches(self.link(), self.filters()))
        fetched = self.link(fetched_at=datetime.datetime(2026, 7, 21))
        self.assertFalse(logic.link_matches(fetched, self.filters()))
        self.assertTrue(logic.link_matches(fetched, self.filters(all="1")))

    def test_dates(self):
        self.assertFalse(logic.link_matches(self.link(), self.filters(since="2026-07-21")))
        self.assertTrue(logic.link_matches(self.link(), self.filters(since="2026-07-20")))
        self.assertFalse(logic.link_matches(self.link(), self.filters(until="2026-07-19")))

    def test_tag_and_star(self):
        self.assertTrue(logic.link_matches(self.link(), self.filters(tag="Health")))
        self.assertFalse(logic.link_matches(self.link(), self.filters(tag="sport")))
        self.assertFalse(logic.link_matches(self.link(), self.filters(starred="1")))
        self.assertTrue(logic.link_matches(self.link(starred=True), self.filters(starred="1")))


class TestCsv(unittest.TestCase):
    def test_csv(self):
        rows = [{"saved": datetime.datetime(2026, 7, 20, 12, 5),
                 "url": "https://x.no/a", "title": 'Tittel, med "komma"',
                 "tags": "health", "note": "", "starred": True, "fetched_at": None}]
        text = logic.links_to_csv(rows)
        lines = text.strip().splitlines()
        self.assertEqual(lines[0], "saved,url,title,tags,note,starred,fetched_at")
        self.assertIn("https://x.no/a", lines[1])
        self.assertIn('"Tittel, med ""komma"""', lines[1])


if __name__ == "__main__":
    unittest.main()
