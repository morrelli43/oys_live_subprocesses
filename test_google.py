import sys, os
sys.path.append('/Users/morrelli43/Documents/GitHub/contact_sync')
from google_connector import GoogleContactsConnector

print("Started")
conn = GoogleContactsConnector(
    credentials_file='/Users/morrelli43/Documents/GitHub/contact_sync/credentials.json',
    token_file='/Users/morrelli43/Documents/GitHub/contact_sync/token.json'
)
contacts = conn.fetch_contacts()
for c in contacts:
    print(f"Name: {c.first_name} {c.last_name}")
    print(f"Email: {c.email}")
    print(f"Phone: {c.phone}")
    print("---")
print("Done")
