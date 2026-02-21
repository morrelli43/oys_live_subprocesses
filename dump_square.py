import os
import sys
from dotenv import load_dotenv

sys.path.append('/Users/morrelli43/Documents/GitHub/contact_sync')
from square_connector import SquareConnector

load_dotenv('/Users/morrelli43/Documents/GitHub/contact_sync/.env')

try:
    square = SquareConnector(access_token=os.getenv('SQUARE_ACCESS_TOKEN'))
    square_contacts = square.fetch_contacts()
    for c in square_contacts:
        print(f"Name: {c.first_name} {c.last_name} | Email: '{c.email}' | Phone: '{c.phone}'")
except Exception as e:
    print(f"Square error: {e}")
