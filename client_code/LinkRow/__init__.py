from ._anvil_designer import LinkRowTemplate
from anvil import *
import anvil.server


class LinkRow(LinkRowTemplate):

    def __init__(self, **properties):
        self.init_components(**properties)
        item = self.item
        self.label_date.text = (item["saved"] or "")[:10]
        self.link_title.text = item["title"] or item["url"]
        self.link_title.url = item["url"]
        self.text_box_tags.text = item["tags"]
        self.text_box_note.text = item["note"]
        self._set_star()

    def _set_star(self):
        self.link_star.text = "★" if self.item["starred"] else "☆"

    def link_star_click(self, **event_args):
        self.item["starred"] = not self.item["starred"]
        anvil.server.call('update_link', self.item["key"], self.item["id"],
                          starred=self.item["starred"])
        self._set_star()

    def text_box_tags_lost_focus(self, **event_args):
        result = anvil.server.call('update_link', self.item["key"],
                                   self.item["id"],
                                   tags=self.text_box_tags.text or "")
        if result["ok"]:
            self.text_box_tags.text = result["tags"]

    def text_box_note_lost_focus(self, **event_args):
        anvil.server.call('update_link', self.item["key"], self.item["id"],
                          note=self.text_box_note.text or "")

    def link_delete_click(self, **event_args):
        anvil.server.call('delete_link', self.item["key"], self.item["id"])
        self.remove_from_parent()
