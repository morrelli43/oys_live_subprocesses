"""
Google Contacts API connector.
"""
from typing import List, Optional
import os
from datetime import datetime

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from contact_model import Contact


class GoogleContactsConnector:
    """Connector for Google Contacts API."""
    
    SCOPES = ['https://www.googleapis.com/auth/contacts']
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google API libraries not installed. Run: pip install -r requirements.txt")
        
        # Validate file paths to prevent directory traversal
        if '..' in credentials_file or '..' in token_file:
            raise ValueError("Invalid file path: directory traversal not allowed")
        
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
    
    def authenticate(self):
        """Authenticate with Google API."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}. "
                        "Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('people', 'v1', credentials=creds)
    
    def fetch_contacts(self) -> List[Contact]:
        """Fetch all contacts from Google."""
        if not self.service:
            self.authenticate()
        
        contacts = []
        page_token = None
        
        while True:
            results = self.service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,emailAddresses,phoneNumbers,organizations,addresses,biographies,userDefined',
                pageToken=page_token
            ).execute()
            
            connections = results.get('connections', [])
            
            for person in connections:
                contact = self._convert_to_contact(person)
                if contact:
                    contacts.append(contact)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        return contacts
    
    def _convert_to_contact(self, person: dict) -> Optional[Contact]:
        """Convert Google person object to Contact."""
        contact = Contact()
        
        # Extract name
        names = person.get('names', [])
        if names:
            contact.first_name = names[0].get('givenName')
            contact.last_name = names[0].get('familyName')
        
        # Extract email
        emails = person.get('emailAddresses', [])
        if emails:
            contact.email = emails[0].get('value')
        
        # Extract phone
        phones = person.get('phoneNumbers', [])
        if phones:
            contact.phone = phones[0].get('value')
        
        # Extract company
        orgs = person.get('organizations', [])
        if orgs:
            contact.company = orgs[0].get('name')
        
        # Extract addresses
        addresses = person.get('addresses', [])
        for addr in addresses:
            street_full = addr.get('streetAddress', '')
            street_parts = street_full.split('\n')
            street = street_parts[0] if street_parts else ''
            street2 = street_parts[1] if len(street_parts) > 1 else ''
            
            contact.addresses.append({
                'street': street,
                'street2': street2,
                'city': addr.get('city', ''),
                'state': addr.get('region', ''),
                'postal_code': addr.get('postalCode', ''),
                'country': addr.get('country', '')
            })
        
        # Extract notes
        bios = person.get('biographies', [])
        if bios:
            contact.notes = bios[0].get('value')
        
        # Extract user defined fields (custom fields)
        user_defined = person.get('userDefined', [])
        for field in user_defined:
            key = field.get('key')
            value = field.get('value')
            if key and value:
                # Store as is directly in extra_fields
                contact.extra_fields[key] = value
        
        # Store Google resource name
        resource_name = person.get('resourceName')
        if resource_name:
            contact.source_ids['google'] = resource_name
        
        return contact if contact.email or (contact.first_name and contact.last_name) else None
    
    def push_contact(self, contact: Contact) -> bool:
        """Push a contact to Google Contacts."""
        if not self.service:
            self.authenticate()
        
        try:
            # Check if contact already exists in Google
            if 'google' in contact.source_ids:
                # Update existing contact
                self._update_contact(contact)
            else:
                # Create new contact
                self._create_contact(contact)
            return True
        except Exception as e:
            print(f"Error pushing contact to Google: {e}")
            return False
    
    def _create_contact(self, contact: Contact):
        """Create a new contact in Google."""
        person = self._contact_to_person(contact)
        
        result = self.service.people().createContact(
            body=person
        ).execute()
        
        # Store the new resource name
        contact.source_ids['google'] = result.get('resourceName')
    
    def _update_contact(self, contact: Contact):
        """Update an existing contact in Google."""
        resource_name = contact.source_ids['google']
        person = self._contact_to_person(contact)
        
        # Get current contact to retrieve etag
        current = self.service.people().get(
            resourceName=resource_name,
            personFields='names'
        ).execute()
        
        person['etag'] = current.get('etag')
        
        self.service.people().updateContact(
            resourceName=resource_name,
            updatePersonFields='names,emailAddresses,phoneNumbers,organizations,addresses,biographies,userDefined',
            body=person
        ).execute()
    
    def _contact_to_person(self, contact: Contact) -> dict:
        """Convert Contact to Google person object."""
        person = {}
        
        # Name
        if contact.first_name or contact.last_name:
            person['names'] = [{
                'givenName': contact.first_name or '',
                'familyName': contact.last_name or ''
            }]
        
        # Email
        if contact.email:
            person['emailAddresses'] = [{'value': contact.email}]
        
        # Phone
        if contact.phone:
            person['phoneNumbers'] = [{'value': contact.phone}]
        
        # Company
        if contact.company:
            person['organizations'] = [{'name': contact.company}]
        
        # Addresses
        if contact.addresses:
            person['addresses'] = []
            for addr in contact.addresses:
                street_parts = [addr.get('street', '')]
                street2 = addr.get('street2', '')
                if street2:
                    street_parts.append(street2)
                
                person['addresses'].append({
                    'streetAddress': "\n".join(street_parts),
                    'city': addr.get('city', ''),
                    'region': addr.get('state', ''),
                    'postalCode': addr.get('postal_code', ''),
                    'country': addr.get('country', '')
                })
        
        # Notes
        if contact.notes:
            person['biographies'] = [{'value': contact.notes}]
            
        # User Defined Fields (Custom Fields)
        if contact.extra_fields:
            person['userDefined'] = []
            for key, value in contact.extra_fields.items():
                person['userDefined'].append({
                    'key': key,
                    'value': value
                })
        
        return person
