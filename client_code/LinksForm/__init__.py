from ._anvil_designer import LinksFormTemplate
from anvil import *
import anvil.server
import anvil.media


class LinksForm(LinksFormTemplate):

    def __init__(self, key=None, **properties):
        self.init_components(**properties)
        self.key = (key or "").strip()
        self.drop_down_mode.items = [
            ("Email me the link", "email"),
            ("Save to My links", "save"),
            ("Email and save", "both"),
        ]
        if self.key:
            self.load()

    def load(self):
        settings = anvil.server.call('get_settings', self.key)
        if not settings["ok"]:
            self.label_status.text = settings["error"]
            return
        self.text_box_key.visible = False
        self.button_open.visible = False
        self.settings_panel.visible = True
        self.actions_panel.visible = True
        self.label_status.text = settings["email"]
        self.drop_down_mode.selected_value = settings["mode"]
        self.text_box_current_tag.text = settings["current_tag"]
        result = anvil.server.call('get_my_links', self.key)
        if result["ok"]:
            for item in result["links"]:
                item["key"] = self.key
            self.repeating_panel_links.items = result["links"]

    def button_open_click(self, **event_args):
        self.key = (self.text_box_key.text or "").strip()
        if self.key:
            self.load()

    def text_box_key_pressed_enter(self, **event_args):
        self.button_open_click()

    def button_save_settings_click(self, **event_args):
        result = anvil.server.call('save_settings', self.key,
                                   self.drop_down_mode.selected_value,
                                   self.text_box_current_tag.text or "")
        if result["ok"]:
            self.label_status.text = "Settings saved."
        else:
            self.label_status.text = result["error"]

    def button_export_click(self, **event_args):
        media = anvil.server.call('export_csv', self.key)
        if media:
            anvil.media.download(media)

    def button_delete_all_click(self, **event_args):
        if confirm("Delete ALL your saved links? This cannot be undone."):
            anvil.server.call('delete_all_links', self.key)
            self.repeating_panel_links.items = []
