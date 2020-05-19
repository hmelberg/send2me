from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class Form1(Form1Template):

  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def email_pressed_enter(self, **event_args):
    path = 'https://scented-perfect-raccoon.anvil.app/_/api'
    email=self.email.text
    self.link.url = f"javascript:fetch('{path}/send/{email}');"
    self.appear.visible=False
    self.link.visible=True


  def create_link_click(self, **event_args):
    path = 'https://scented-perfect-raccoon.anvil.app/_/api'
    email=self.email.text
    self.link.url = f"javascript:fetch('{path}/send/{email}');"
    self.appear.visible=False
    self.link.visible=True

#https://stackoverflow.com/questions/463368/javascript-close-alert-box/45152906#45152906

#https://www.iconfinder.com/icons/3246742/paperplane_software_telegram_icon
#https://stackoverflow.com/questions/3024745/cross-browser-bookmark-add-to-favorites-javascript
#https://sandbox.self.li/bookmarklet-to-extension/






