from ._anvil_designer import RegisterFormTemplate
from anvil import *
import anvil.server


class RegisterForm(RegisterFormTemplate):

    def __init__(self, **properties):
        self.init_components(**properties)

    def button_register_click(self, **event_args):
        self.label_reg_status.text = "Sender ..."
        result = anvil.server.call('register_email', self.text_box_email.text or "")
        if result["ok"]:
            self.label_reg_status.text = "Sjekk innboksen din!"
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
            self.label_step3.visible = True
        else:
            self.label_make_status.text = result["error"]

    def text_box_token_pressed_enter(self, **event_args):
        self.button_make_click()
