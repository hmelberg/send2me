from ._anvil_designer import RegisterFormTemplate
from anvil import *
import anvil.server


class RegisterForm(RegisterFormTemplate):

    def __init__(self, **properties):
        self.init_components(**properties)
        params = get_url_hash()
        if isinstance(params, dict) and params.get("key"):
            open_form('LinksForm', key=params["key"])

    def button_register_click(self, **event_args):
        self.label_reg_status.text = "Sending ..."
        result = anvil.server.call('register_email', self.text_box_email.text or "")
        if result["ok"]:
            self.label_reg_status.text = "Check your inbox!"
        else:
            self.label_reg_status.text = result["error"]

    def text_box_email_pressed_enter(self, **event_args):
        self.button_register_click()

    def button_make_click(self, **event_args):
        self.label_make_status.text = ""
        result = anvil.server.call('make_bookmarklet', self.text_box_token.text or "")
        if result["ok"]:
            self.link_bookmarklet.url = result["js"]
            self.link_bookmarklet.visible = True
            self.link_mylinks.url = result["links_url"]
            self.link_mylinks.visible = True
            self.label_step3.visible = True
        else:
            self.label_make_status.text = result["error"]

    def text_box_token_pressed_enter(self, **event_args):
        self.button_make_click()
