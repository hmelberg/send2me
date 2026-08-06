from ._anvil_designer import LinksFormTemplate
from anvil import *
import anvil.server
import anvil.media

from .. import links_view
from ..SettingsForm import SettingsForm

SORT_ARROWS = {True: " ▾", False: " ▴"}
HEAD_TEXT = {"stars": "★", "saved": "Date", "title": "Title"}


class LinksForm(LinksFormTemplate):
    """The archive page. Links load once and are filtered in the browser;
    everything that is not a link sits behind the cog or in a column header."""

    def __init__(self, key=None, **properties):
        self.init_components(**properties)
        self.key = (key or "").strip()
        self.links = []
        self.sort_key = "saved"
        self.sort_descending = True
        self.saved_tag = None
        self.limit = links_view.PAGE_SIZE
        self.selected_ids = set()
        self._matched_ids = []
        self.repeating_panel_links.set_event_handler(
            'x-link-deleted', self.link_deleted)
        self.repeating_panel_links.set_event_handler(
            'x-tags-changed', self.tags_changed)
        self.repeating_panel_links.set_event_handler(
            'x-selected-changed', self.link_selected_changed)
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
        self.actions_panel.visible = True
        self.tag_panel.visible = True
        self.link_export.visible = True
        self.link_settings.visible = True
        self.head_panel.visible = True
        self.text_box_current_tag.text = settings["current_tag"]
        self.saved_tag = settings["current_tag"]
        result = anvil.server.call('get_my_links', self.key)
        if not result["ok"]:
            self._status(result["error"])
            return
        self.links = result["links"]
        for link in self.links:
            link["key"] = self.key
        self.selected_ids = links_view.prune_selection(self.selected_ids,
                                                       self.links)
        self._fill_tag_options()
        self._refresh()

    def _fill_tag_options(self):
        """The tag filter lives in the Tags column header, so its idle state
        has to read as that header rather than as an empty dropdown."""
        chosen = self.drop_down_tag.selected_value
        tags = links_view.all_tags(self.links)
        self.drop_down_tag.items = [("Tags", "")] + [(t, t) for t in tags]
        self.drop_down_tag.selected_value = chosen if chosen in tags else ""

    # ---------- filtering, sorting, drawing ----------

    def _refresh(self):
        """Filter and sort the whole set, then cut. Cutting last is what lets
        a search reach links that are not on screen yet."""
        search = self.text_box_search.text or ""
        tag = self.drop_down_tag.selected_value or ""
        matched = links_view.filter_links(self.links, search=search, tag=tag)
        matched = links_view.sort_links(matched, self.sort_key,
                                        self.sort_descending)
        self._matched_ids = [l["id"] for l in matched]
        shown = matched[:self.limit]
        for link in shown:
            link["selected"] = link["id"] in self.selected_ids
        self.repeating_panel_links.items = shown
        self._show_selection()
        self.link_clear.visible = bool(search or tag)
        label = links_view.page_label(len(shown), len(matched))
        self.label_shown.text = label
        self.footer_panel.visible = bool(label)
        self.label_empty.visible = not shown
        self.label_empty.text = ("Nothing saved yet - click your send2me bookmark "
                                 "on any page." if not self.links
                                 else "No links match your filters.")

    # ---------- selection ----------

    def _show_selection(self):
        """The pill in the toolbar is the selection's only permanent trace -
        marked rows can be scrolled away or filtered out of sight."""
        n = len(self.selected_ids)
        self.check_box_all.checked = links_view.all_selected(
            self.selected_ids, self._matched_ids)
        self.link_selected.text = (links_view.selection_label(n) + " ✕") if n else ""
        self.link_selected.visible = bool(n)
        self.link_export.tooltip = ("Export %d selected as CSV" % n if n
                                    else "Export CSV")

    def select_all_changed(self, **event_args):
        """Acts on every matched link, not just the drawn page, and only on
        the matched ones - picks made under other filters survive, so a
        selection can be built up filter by filter."""
        self.selected_ids = links_view.toggle_select_all(
            self.selected_ids, self._matched_ids)
        self._refresh()

    def link_selected_changed(self, link, selected, **event_args):
        if selected:
            self.selected_ids.add(link["id"])
        else:
            self.selected_ids.discard(link["id"])
        self._show_selection()

    def link_selected_click(self, **event_args):
        self.selected_ids = set()
        self._refresh()

    def link_more_click(self, **event_args):
        self.limit += links_view.PAGE_SIZE
        self._refresh()

    def filter_changed(self, **event_args):
        # a new filter is a new question - start from the top again
        self.limit = links_view.PAGE_SIZE
        self._refresh()

    def link_clear_click(self, **event_args):
        self.text_box_search.text = ""
        self.drop_down_tag.selected_value = ""
        self.limit = links_view.PAGE_SIZE
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
        self.selected_ids.discard(link["id"])
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
        form = SettingsForm(key=self.key)
        alert(form, title="Settings", buttons=[("Close", None)])
        if form.deleted_all:
            self.links = []
            self.selected_ids = set()
            self._fill_tag_options()
            self._refresh()

    def current_tag_saved(self, **event_args):
        tag = self.text_box_current_tag.text or ""
        if not self.key or tag == self.saved_tag:
            return
        result = anvil.server.call('save_settings', self.key, current_tag=tag)
        if not result["ok"]:
            self._status(result["error"])
            return
        self.text_box_current_tag.text = result["current_tag"]
        self.saved_tag = result["current_tag"]
        self._status("Saving new links as: " + (result["current_tag"] or "no tag"))

    def link_export_click(self, **event_args):
        ids = sorted(self.selected_ids) if self.selected_ids else None
        media = anvil.server.call('export_csv', self.key, ids=ids)
        if media:
            anvil.media.download(media)

    def _status(self, text):
        self.label_status.text = text
        self.label_status.visible = bool(text)
