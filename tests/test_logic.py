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

    def test_popup_shows_sending_before_the_server_answers(self):
        js = logic.bookmarklet_js("TOKEN123")
        self.assertIn("window.open(''", js)           # apnes tomt ...
        self.assertIn("document.write('Sending", js)  # ... med placeholder ...
        self.assertIn("w.location=u", js)             # ... og navigeres sa
        # gjenbrukt vindu fra forrige sending star pa et annet origin, og da
        # kaster document.write - navigasjonen skal skje uansett
        self.assertIn("try{", js)


class TestTexts(unittest.TestCase):
    def test_email_text(self):
        txt = logic.registration_email_text(
            "TOK", "javascript:x", "https://send2me.app/#?key=TOK")
        self.assertIn("TOK", txt)
        self.assertIn("javascript:x", txt)
        self.assertIn("https://send2me.app/#?key=TOK", txt)

    def test_email_states_the_mode_default_and_the_limits(self):
        txt = logic.registration_email_text("TOK", "js", "url")
        self.assertIn("Both is", txt)
        self.assertIn("Settings", txt)
        self.assertIn("%d months" % logic.RETENTION_MONTHS, txt)
        self.assertIn("%d" % logic.MAX_LINKS, txt)
        self.assertIn("cannot", txt)
        # the small print belongs at the end, after the setup steps
        self.assertGreater(txt.index("Small print"), txt.index("On your phone"))


class TestLinkCap(unittest.TestCase):
    def links(self, n, starred=()):
        return [{"id": "L%d" % i, "saved": datetime.datetime(2026, 1, 1) +
                 datetime.timedelta(days=i), "stars": 3 if i in starred else 0}
                for i in range(n)]

    def test_under_cap_deletes_nothing(self):
        self.assertEqual(logic.links_over_cap(self.links(5), 5), [])
        self.assertEqual(logic.links_over_cap([], 5), [])

    def test_oldest_go_first(self):
        self.assertEqual(logic.links_over_cap(self.links(8), 5),
                         ["L0", "L1", "L2"])

    def test_order_of_input_does_not_matter(self):
        shuffled = list(reversed(self.links(8)))
        self.assertEqual(sorted(logic.links_over_cap(shuffled, 5)),
                         ["L0", "L1", "L2"])

    def test_starred_links_are_spared(self):
        # L0 and L1 are the oldest but starred, so L2..L4 go instead
        self.assertEqual(logic.links_over_cap(self.links(8, starred=(0, 1)), 5),
                         ["L2", "L3", "L4"])

    def test_starred_only_as_a_last_resort(self):
        got = logic.links_over_cap(self.links(8, starred=tuple(range(8))), 5)
        self.assertEqual(got, ["L0", "L1", "L2"])

    def test_default_cap_is_the_number_in_the_email(self):
        self.assertEqual(logic.links_over_cap(self.links(logic.MAX_LINKS)), [])
        self.assertEqual(len(logic.links_over_cap(self.links(logic.MAX_LINKS + 3))), 3)

    def test_sent_page(self):
        html = logic.sent_page_html()
        self.assertIn("Sent", html)
        self.assertIn("window.close", html)
        self.assertIn("history.back", html)
        self.assertIn("Saved", logic.sent_page_html("Saved"))

    def test_sent_page_closes_fast(self):
        # nedtellingen starter forst etter at serveren har svart, sa et lavt
        # tall kan ikke miste lenker - 300 ms er nok til a se haken
        self.assertIn("}},300)", logic.sent_page_html())

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
        self.assertEqual(f["min_stars"], 0)

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
        self.assertEqual(f["min_stars"], 1)

    def test_stars_overrides_starred_alias(self):
        f, err = logic.parse_links_query({"stars": "3", "starred": "1"})
        self.assertIsNone(err)
        self.assertEqual(f["min_stars"], 3)
        f, _ = logic.parse_links_query({"stars": "9"})
        self.assertEqual(f["min_stars"], 3)

    def test_bad_stars(self):
        f, err = logic.parse_links_query({"stars": "mange"})
        self.assertIsNone(f)
        self.assertIn("stars", err)

    def test_bad_date(self):
        f, err = logic.parse_links_query({"since": "01.07.2026"})
        self.assertIsNone(f)
        self.assertIn("since", err)


class TestStars(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(logic.clamp_stars(2), 2)
        self.assertEqual(logic.clamp_stars(7), 3)
        self.assertEqual(logic.clamp_stars(-1), 0)
        self.assertEqual(logic.clamp_stars(None), 0)
        self.assertEqual(logic.clamp_stars("tull"), 0)

    def test_fallback_to_old_starred_column(self):
        self.assertEqual(logic.link_stars(None, True), 1)
        self.assertEqual(logic.link_stars(None, False), 0)
        self.assertEqual(logic.link_stars(0, True), 0)
        self.assertEqual(logic.link_stars(3, False), 3)


class TestLinkMatches(unittest.TestCase):
    def link(self, **kw):
        base = {"saved": datetime.datetime(2026, 7, 20, 12, 0),
                "fetched_at": None, "tags": "health, econ", "stars": 0}
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

    def test_tag(self):
        self.assertTrue(logic.link_matches(self.link(), self.filters(tag="Health")))
        self.assertFalse(logic.link_matches(self.link(), self.filters(tag="sport")))

    def test_min_stars(self):
        self.assertFalse(logic.link_matches(self.link(), self.filters(stars="1")))
        self.assertTrue(logic.link_matches(self.link(stars=2), self.filters(stars="1")))
        self.assertFalse(logic.link_matches(self.link(stars=2), self.filters(stars="3")))
        self.assertTrue(logic.link_matches(self.link(stars=3), self.filters(stars="3")))

    def test_old_starred_row_counts_as_one_star(self):
        old = self.link(stars=None, starred=True)
        self.assertTrue(logic.link_matches(old, self.filters(starred="1")))
        self.assertFalse(logic.link_matches(old, self.filters(stars="2")))


class TestLinksByIds(unittest.TestCase):
    links = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

    def test_subset_keeps_saved_order(self):
        self.assertEqual(logic.links_by_ids(self.links, ["c", "a"]),
                         [{"id": "a"}, {"id": "c"}])

    def test_no_selection_means_everything(self):
        self.assertEqual(logic.links_by_ids(self.links, None), self.links)
        self.assertEqual(logic.links_by_ids(self.links, []), self.links)

    def test_unknown_ids_are_ignored(self):
        self.assertEqual(logic.links_by_ids(self.links, ["b", "ukjent"]),
                         [{"id": "b"}])


class TestCsv(unittest.TestCase):
    def test_csv(self):
        rows = [{"saved": datetime.datetime(2026, 7, 20, 12, 5),
                 "url": "https://x.no/a", "title": 'Tittel, med "komma"',
                 "tags": "health", "note": "", "stars": 2, "fetched_at": None}]
        text = logic.links_to_csv(rows)
        lines = text.strip().splitlines()
        self.assertEqual(lines[0], "saved,url,title,tags,note,stars,fetched_at")
        self.assertIn("https://x.no/a", lines[1])
        self.assertIn('"Tittel, med ""komma"""', lines[1])
        self.assertTrue(lines[1].endswith(",2,"))

    def test_csv_old_row_without_stars_column(self):
        rows = [{"saved": datetime.datetime(2026, 7, 20, 12, 5),
                 "url": "https://x.no/a", "title": "T", "tags": "", "note": "",
                 "stars": None, "starred": True, "fetched_at": None}]
        self.assertTrue(logic.links_to_csv(rows).strip().endswith(",1,"))


if __name__ == "__main__":
    unittest.main()
