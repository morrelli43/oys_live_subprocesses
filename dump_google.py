import sys
from dotenv import load_dotenv

sys.path.append('/Users/morrelli43/Documents/GitHub/contact_sync')
from google_connector import GoogleContactsConnector

load_dotenv('/Users/morrelli43/Documents/GitHub/contact_sync/.env')

google = GoogleContactsConnector()
google_contacts = google.fetch_contacts()
for c in google_contacts:
    print(f"Name: {c.first_name} {c.last_name} | Email: '{c.email}' | Phone: '{c.phone}'")
