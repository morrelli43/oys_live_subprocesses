import sys
from dotenv import load_dotenv

sys.path.append('/Users/morrelli43/Documents/GitHub/contact_sync')
from google_connector import GoogleContactsConnector

load_dotenv('/Users/morrelli43/Documents/GitHub/contact_sync/.env')

try:
    google = GoogleContactsConnector()
    google_contacts = google.fetch_contacts()
    for c in google_contacts:
        name = f"{c.first_name} {c.last_name}"
        if "Adam" in name or "Marcus" in name:
            print(f"Name: {name}")
            print(f"Email: '{c.email}'")
            print(f"Phone: '{c.phone}'")
            print(f"ID: {c.source_ids.get('google')}")
            print("---")
except Exception as e:
    print(f"Google error: {e}")
