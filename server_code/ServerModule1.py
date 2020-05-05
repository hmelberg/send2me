import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.email
import anvil.server

import anvil.server


@anvil.server.http_endpoint("/send/:email")
def send_url(email):
  ip = anvil.server.request.remote_address
  url=anvil.server.request.origin
  body=anvil.server.request.body_json
  headers=anvil.server.request.headers
  
  print('url',url)
  print('ip',ip)
  print('body',body)
  print('headers', headers)
  
  anvil.email.send(from_name="send2me", 
                 to=email, 
                 subject="Link",
                 text=ip)



