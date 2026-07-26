from ._anvil_designer import LinksFormTemplate
from anvil import *
import anvil.server
import anvil.media
import datetime

from .. import links_view

SORT_ARROWS = {True: " ▾", False: " ▴"}
HEAD_TEXT = {"stars": "★", "saved": "Date", "title": "Title"}


class LinksForm(LinksFormTemplate):
    """The archive page. Links are loaded once and filtered in the browser;
    everything that is not a link lives behind the settings cog."""

    def __init__(self, key=None, **properties):
        self.init_components(**properties)
        self.key = (key or "").strip()
        self.links = []
        self.sort_key = "saved"
        self.sort_descending = True
        self.saved_mode = None
        self.saved_tag = None
        self.drop_down_mode.items = [
            ("Email me the link", "email"),
            ("Save to My links", "save"),
            ("Email and save", "both"),
        ]
        self.drop_down_date.items = list(links_view.DATE_PRESETS)
        self.drop_down_date.selected_value = ""
        self.repeating_panel_links.set_event_handler(
            'x-link-deleted', self.link_deleted)
        self.repeating_panel_links.set_event_handler(
            'x-tags-changed', self.tags_changed)
        self._show_sort_arrow()
        if self.key:
            self.load()

    # ---------- loading ----------

    def load(self):
        settings = anvil.server.call('get_settings', self.key)
        if not settings["ok"]:
            self._status(settings["error"])
            return
        self._status("")
        self.login_panel.visible = False
        self.tag_panel.visible = True
        self.link_export.visible = True
        self.link_settings.visible = True
        self.toolbar_panel.visible = True
        self.head_panel.visible = True
        self.label_email.text = "Signed in as " + settings["email"]
        self.drop_down_mode.selected_value = settings["mode"]
        self.text_box_current_tag.text = settings["current_tag"]
        self.saved_mode = settings["mode"]
        self.saved_tag = settings["current_tag"]
        result = anvil.server.call('get_my_links', self.key)
        if not result["ok"]:
            self._status(result["error"])
            return
        self.links = result["links"]
        for link in self.links:
            link["key"] = self.key
        self._fill_tag_options()
        self._refresh()

    def _fill_tag_options(self):
        chosen = self.drop_down_tag.selected_value
        tags = links_view.all_tags(self.links)
        self.drop_down_tag.items = [("All tags", "")] + [(t, t) for t in tags]
        self.drop_down_tag.selected_value = chosen if chosen in tags else ""

    # ---------- filtering, sorting, drawing ----------

    def _refresh(self):
        since = links_view.cutoff(self.drop_down_date.selected_value,
                                  datetime.date.today())
        shown = links_view.filter_links(self.links,
                                        search=self.text_box_search.text or "",
                                        tag=self.drop_down_tag.selected_value or "",
                                        since=since)
        shown = links_view.sort_links(shown, self.sort_key, self.sort_descending)
        self.repeating_panel_links.items = shown
        self.label_count.text = links_view.count_label(len(shown), len(self.links))
        self.label_empty.visible = not shown
        self.label_empty.text = ("Nothing saved yet - click your send2me bookmark "
                                 "on any page." if not self.links
                                 else "No links match your filters.")

    def filter_changed(self, **event_args):
        self._refresh()

    def link_clear_click(self, **event_args):
        self.text_box_search.text = ""
        self.drop_down_tag.selected_value = ""
        self.drop_down_date.selected_value = ""
        self._refresh()

    def _sort_by(self, key):
        if self.sort_key == key:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_key = key
            self.sort_descending = key != "title"
        self._show_sort_arrow()
        self._refresh()

    def _show_sort_arrow(self):
        heads = {"stars": self.link_head_stars, "saved": self.link_head_date,
                 "title": self.link_head_title}
        for key, head in heads.items():
            head.text = HEAD_TEXT[key]
        heads[self.sort_key].text += SORT_ARROWS[self.sort_descending]

    def sort_by_stars(self, **event_args):
        self._sort_by("stars")

    def sort_by_date(self, **event_args):
        self._sort_by("saved")

    def sort_by_title(self, **event_args):
        self._sort_by("title")

    # ---------- events from the rows ----------

    def link_deleted(self, link, **event_args):
        self.links = [l for l in self.links if l["id"] != link["id"]]
        self._fill_tag_options()
        self._refresh()

    def tags_changed(self, **event_args):
        self._fill_tag_options()

    # ---------- key, settings ----------

    def button_open_click(self, **event_args):
        self.key = (self.text_box_key.text or "").strip()
        if self.key:
            self.load()

    def text_box_key_pressed_enter(self, **event_args):
        self.button_open_click()

    def link_settings_click(self, **event_args):
        self.settings_panel.visible = not self.settings_panel.visible

    def current_tag_saved(self, **event_args):
        self._save_settings("Saving new links as: ")

    def mode_changed(self, **event_args):
        self._save_settings()

    def _save_settings(self, prefix=None):
        """Both settings save themselves; nothing to press. Skipped when
        neither has actually changed, so leaving the tag box costs nothing."""
        mode = self.drop_down_mode.selected_value
        tag = self.text_box_current_tag.text or ""
        if not self.key or (mode == self.saved_mode and tag == self.saved_tag):
            return
        result = anvil.server.call('save_settings', self.key, mode, tag)
        if not result["ok"]:
            self._status(result["error"])
            return
        self.text_box_current_tag.text = result["current_tag"]
        self.saved_mode = mode
        self.saved_tag = result["current_tag"]
        if prefix is None:
            self._status("Settings saved.")
        else:
            self._status(prefix + (result["current_tag"] or "no tag"))

    def link_export_click(self, **event_args):
        media = anvil.server.call('export_csv', self.key)
        if media:
            anvil.media.download(media)

    def button_delete_all_click(self, **event_args):
        if confirm("Delete ALL your saved links? This cannot be undone."):
            anvil.server.call('delete_all_links', self.key)
            self.links = []
            self._fill_tag_options()
            self._refresh()

    def _status(self, text):
        self.label_status.text = text
        self.label_status.visible = bool(text)
