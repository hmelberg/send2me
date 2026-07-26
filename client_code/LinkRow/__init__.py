from ._anvil_designer import LinkRowTemplate
from anvil import *
import anvil.server
import datetime

from .. import links_view

STAR_ON = "#F5A623"
STAR_OFF = "#D6DBE0"
NOTE_ON = "#1976D2"
NOTE_OFF = "#C2C9D0"


class LinkRow(LinkRowTemplate):
    """One saved link on one row. Edits save themselves; the parent
    RepeatingPanel hears about changes through x-link-* events."""

    def __init__(self, **properties):
        self.init_components(**properties)
        item = self.item
        day = links_view.day_of(item)
        self.label_date.text = links_view.format_day(day, datetime.date.today().year)
        self.label_date.tooltip = item["saved"] or ""
        self.link_title.text = item["title"] or item["url"]
        self.link_title.url = item["url"]
        self.link_title.tooltip = item["url"]
        self.text_box_tags.text = item["tags"]
        self.text_box_note.text = item["note"]
        self.note_open = False
        self._show_stars()
        self._show_note_flag()

    def _show_stars(self):
        stars = links_view.stars_of(self.item)
        for n, link in enumerate([self.link_star1, self.link_star2,
                                  self.link_star3], start=1):
            link.foreground = STAR_ON if n <= stars else STAR_OFF

    def _set_stars(self, clicked):
        stars = links_view.next_stars(links_view.stars_of(self.item), clicked)
        self.item["stars"] = stars
        self._show_stars()
        anvil.server.call('update_link', self.item["key"], self.item["id"],
                          stars=stars)

    def link_star1_click(self, **event_args):
        self._set_stars(1)

    def link_star2_click(self, **event_args):
        self._set_stars(2)

    def link_star3_click(self, **event_args):
        self._set_stars(3)

    def text_box_tags_lost_focus(self, **event_args):
        result = anvil.server.call('update_link', self.item["key"],
                                   self.item["id"],
                                   tags=self.text_box_tags.text or "")
        if result["ok"]:
            self.text_box_tags.text = result["tags"]
            self.item["tags"] = result["tags"]
            self.parent.raise_event('x-tags-changed')

    def text_box_tags_pressed_enter(self, **event_args):
        self.text_box_tags_lost_focus()

    def text_box_note_lost_focus(self, **event_args):
        note = self.text_box_note.text or ""
        anvil.server.call('update_link', self.item["key"], self.item["id"],
                          note=note)
        self.item["note"] = note.strip()
        self._show_note_flag()

    def _show_note_flag(self):
        """The icon is lit when there is a note to see, so a folded-away note
        is still discoverable."""
        has_note = bool((self.item["note"] or "").strip())
        self.link_note_toggle.foreground = NOTE_ON if has_note else NOTE_OFF

    def link_note_toggle_click(self, **event_args):
        """Only shown on narrow screens, where the note is folded away to keep
        each link down to two lines. The role swap is what reveals it."""
        self.note_open = not self.note_open
        self.text_box_note.role = "row-note-open" if self.note_open else "row-note"
        if self.note_open:
            self.text_box_note.focus()

    def text_box_note_pressed_enter(self, **event_args):
        self.text_box_note_lost_focus()

    def link_delete_click(self, **event_args):
        anvil.server.call('delete_link', self.item["key"], self.item["id"])
        self.parent.raise_event('x-link-deleted', link=self.item)
