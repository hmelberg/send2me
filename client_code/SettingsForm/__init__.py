from ._anvil_designer import SettingsFormTemplate
from anvil import *
import anvil.server


class SettingsForm(SettingsFormTemplate):
    """Shown in a modal from the cog. Holds the things you set once, plus a
    way to get the bookmark link back on a machine that never had it."""

    def __init__(self, key=None, **properties):
        self.init_components(**properties)
        self.key = (key or "").strip()
        self.deleted_all = False
        self.drop_down_mode.items = [
            ("Email me the link", "email"),
            ("Save to My links", "save"),
            ("Email and save", "both"),
        ]
        settings = anvil.server.call('get_settings', self.key)
        if not settings["ok"]:
            self._status(settings["error"])
            return
        self.label_email.text = settings["email"]
        self.drop_down_mode.selected_value = settings["mode"]
        self.saved_mode = settings["mode"]
        bookmark = anvil.server.call('make_bookmarklet', self.key)
        if bookmark["ok"]:
            self.link_bookmarklet.url = bookmark["js"]
            self.link_mylinks.url = bookmark["links_url"]
        else:
            self.bookmark_panel.visible = False
            self.label_bookmark_hint.visible = False

    def mode_changed(self, **event_args):
        mode = self.drop_down_mode.selected_value
        if mode == self.saved_mode:
            return
        result = anvil.server.call('save_settings', self.key, mode=mode)
        if result["ok"]:
            self.saved_mode = result["mode"]
            self._status("Saved.")
        else:
            self._status(result["error"])

    def link_delete_all_click(self, **event_args):
        if not confirm("Delete ALL your saved links?\n\n"
                       "This cannot be undone. Export CSV first if you want "
                       "to keep a copy.",
                       dismissible=True, buttons=[("Delete everything", True),
                                                  ("Cancel", False)]):
            return
        result = anvil.server.call('delete_all_links', self.key)
        if result["ok"]:
            self.deleted_all = True
            self._status("Deleted %d links." % result["deleted"])
        else:
            self._status(result["error"])

    def _status(self, text):
        self.label_status.text = text
        self.label_status.visible = bool(text)
