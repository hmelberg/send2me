import sys
import unittest
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "client_code"))
import links_view as lv


def link(saved="2026-07-20 12:00", title="Helseatlas", url="https://x.no/a",
         tags="health, econ", note="les kap 3", **kw):
    d = {"saved": saved, "title": title, "url": url, "tags": tags, "note": note}
    d.update(kw)
    return d


class TestStars(unittest.TestCase):
    def test_plain_value(self):
        self.assertEqual(lv.stars_of(link(stars=2)), 2)
        self.assertEqual(lv.stars_of(link(stars=0)), 0)

    def test_clamped(self):
        self.assertEqual(lv.stars_of(link(stars=9)), 3)
        self.assertEqual(lv.stars_of(link(stars=-4)), 0)
        self.assertEqual(lv.stars_of(link(stars="tull")), 0)

    def test_missing_value_is_no_stars(self):
        self.assertEqual(lv.stars_of(link(stars=None)), 0)
        self.assertEqual(lv.stars_of(link()), 0)

    def test_next_stars_toggles(self):
        self.assertEqual(lv.next_stars(0, 1), 1)
        self.assertEqual(lv.next_stars(1, 3), 3)
        self.assertEqual(lv.next_stars(2, 1), 1)
        self.assertEqual(lv.next_stars(2, 2), 0)


class TestDates(unittest.TestCase):
    today = datetime.date(2026, 7, 26)

    def test_day_of(self):
        self.assertEqual(lv.day_of(link()), "2026-07-20")
        self.assertEqual(lv.day_of({}), "")

    def test_format_day(self):
        self.assertEqual(lv.format_day("2026-07-20", 2026), "07-20")
        self.assertEqual(lv.format_day("2025-12-31", 2026), "2025-12-31")
        self.assertEqual(lv.format_day("", 2026), "")


class TestTags(unittest.TestCase):
    def test_tags_of(self):
        self.assertEqual(lv.tags_of(link(tags="a,  b ,,c")), ["a", "b", "c"])
        self.assertEqual(lv.tags_of(link(tags="")), [])
        self.assertEqual(lv.tags_of(link(tags=None)), [])

    def test_all_tags_unique_and_sorted(self):
        links = [link(tags="Health, econ"), link(tags="health"), link(tags="ssb")]
        self.assertEqual(lv.all_tags(links), ["econ", "Health", "ssb"])


class TestFilter(unittest.TestCase):
    links = [
        link(title="Helseatlas", tags="health", note="les kap 3",
             saved="2026-07-25 09:00"),
        link(title="SSB tabell 07459", tags="data, ssb", note="",
             saved="2026-07-10 09:00", url="https://ssb.no/07459"),
        link(title="Lancet obesity", tags="health", note="til motet",
             saved="2026-01-02 09:00"),
    ]

    def test_no_filters_keeps_all(self):
        self.assertEqual(len(lv.filter_links(self.links)), 3)

    def test_search_hits_title(self):
        got = lv.filter_links(self.links, search="lancet")
        self.assertEqual([l["title"] for l in got], ["Lancet obesity"])

    def test_search_hits_note(self):
        got = lv.filter_links(self.links, search="MOTET")
        self.assertEqual([l["title"] for l in got], ["Lancet obesity"])

    def test_search_hits_url_and_tags(self):
        self.assertEqual(len(lv.filter_links(self.links, search="07459")), 1)
        self.assertEqual(len(lv.filter_links(self.links, search="health")), 2)

    def test_tag_is_exact_not_substring(self):
        self.assertEqual(len(lv.filter_links(self.links, tag="Health")), 2)
        self.assertEqual(len(lv.filter_links(self.links, tag="heal")), 0)

    def test_filters_combine(self):
        got = lv.filter_links(self.links, search="tabell", tag="ssb")
        self.assertEqual(len(got), 1)
        self.assertEqual(len(lv.filter_links(self.links, search="tabell",
                                             tag="health")), 0)


class TestSort(unittest.TestCase):
    links = [
        link(title="Beta", saved="2026-07-10 09:00", stars=3),
        link(title="alpha", saved="2026-07-25 09:00", stars=0),
        link(title="Gamma", saved="2026-07-20 09:00", stars=3),
    ]

    def titles(self, **kw):
        return [l["title"] for l in lv.sort_links(self.links, **kw)]

    def test_newest_first(self):
        self.assertEqual(self.titles(), ["alpha", "Gamma", "Beta"])

    def test_oldest_first(self):
        self.assertEqual(self.titles(descending=False),
                         ["Beta", "Gamma", "alpha"])

    def test_stars_then_newest(self):
        self.assertEqual(self.titles(key="stars"), ["Gamma", "Beta", "alpha"])

    def test_title_is_case_insensitive(self):
        self.assertEqual(self.titles(key="title", descending=False),
                         ["alpha", "Beta", "Gamma"])

    def test_sort_does_not_mutate_input(self):
        before = [l["title"] for l in self.links]
        lv.sort_links(self.links, key="title")
        self.assertEqual([l["title"] for l in self.links], before)


if __name__ == "__main__":
    unittest.main()
