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
    path = 'https://scented-perfect-raccoon.anvil.app/_/api/'
    email=self.email.text
    self.link.url = path+f'send/{email}'



