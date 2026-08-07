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
        self.check_encrypt.checked = bool(settings.get("encrypted"))
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

    def encrypt_changed(self, **event_args):
        turn_on = self.check_encrypt.checked
        if turn_on:
            ok = confirm("Encrypt your saved links?\n\n"
                         "Your key becomes the only way to read them. If you "
                         "lose it and register again, your saved links will "
                         "be deleted. Export CSV first if you want a plain copy.",
                         dismissible=True,
                         buttons=[("Encrypt my links", True), ("Cancel", False)])
        else:
            ok = confirm("Turn off encryption?\n\n"
                         "Your saved links will be stored as plain text again.",
                         dismissible=True,
                         buttons=[("Turn off", True), ("Cancel", False)])
        if not ok:
            self.check_encrypt.checked = not turn_on
            return
        try:
            result = anvil.server.call('save_settings', self.key,
                                       encrypt=turn_on)
        except Exception:
            # Timeout eller serverfeil: vi vet ikke hvor langt den kom, sa vi
            # henter fasit i stedet for a gjette pa checkbox-tilstanden.
            self._sync_encrypt_state()
            self._status("Something went wrong. Check the box above - "
                         "try again if it is not what you wanted.")
            return
        if result["ok"]:
            if turn_on:
                self._status("Encrypted %d links." % (result.get("migrated") or 0))
            else:
                self._status("Encryption turned off.")
        else:
            self.check_encrypt.checked = not turn_on
            self._status(result["error"])

    def _sync_encrypt_state(self):
        try:
            settings = anvil.server.call('get_settings', self.key)
            if settings["ok"]:
                self.check_encrypt.checked = bool(settings.get("encrypted"))
        except Exception:
            pass

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
