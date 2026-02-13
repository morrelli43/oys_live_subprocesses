"""
Square Up API connector.
"""
from typing import List, Optional
import os

try:
    from square.client import Client
    SQUARE_AVAILABLE = True
except ImportError:
    SQUARE_AVAILABLE = False

from contact_model import Contact


class SquareConnector:
    """Connector for Square Up API."""
    
    def __init__(self, access_token: str = None):
        if not SQUARE_AVAILABLE:
            raise ImportError("Square API library not installed. Run: pip install -r requirements.txt")
        
        self.access_token = access_token or os.getenv('SQUARE_ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError("Square access token not provided. Set SQUARE_ACCESS_TOKEN environment variable.")
        
        self.client = Client(
            access_token=self.access_token,
            environment='production'  # Change to 'sandbox' for testing
        )
    
    def fetch_contacts(self) -> List[Contact]:
        """Fetch all customers from Square."""
        contacts = []
        cursor = None
        
        try:
            while True:
                result = self.client.customers.list_customers(cursor=cursor)
                
                if result.is_success():
                    customers = result.body.get('customers', [])
                    
                    for customer in customers:
                        contact = self._convert_to_contact(customer)
                        if contact:
                            contacts.append(contact)
                    
                    cursor = result.body.get('cursor')
                    if not cursor:
                        break
                else:
                    print(f"Error fetching Square customers: {result.errors}")
                    break
        
        except Exception as e:
            print(f"Error connecting to Square API: {e}")
        
        return contacts
    
    def _convert_to_contact(self, customer: dict) -> Optional[Contact]:
        """Convert Square customer to Contact."""
        contact = Contact()
        
        # Extract name
        contact.first_name = customer.get('given_name')
        contact.last_name = customer.get('family_name')
        
        # Extract email
        contact.email = customer.get('email_address')
        
        # Extract phone
        contact.phone = customer.get('phone_number')
        
        # Extract company
        contact.company = customer.get('company_name')
        
        # Extract address
        address = customer.get('address')
        if address:
            contact.addresses.append({
                'street': address.get('address_line_1', ''),
                'city': address.get('locality', ''),
                'state': address.get('administrative_district_level_1', ''),
                'postal_code': address.get('postal_code', ''),
                'country': address.get('country', '')
            })
        
        # Extract notes
        note = customer.get('note')
        if note:
            contact.notes = note
        
        # Store Square customer ID
        customer_id = customer.get('id')
        if customer_id:
            contact.source_ids['square'] = customer_id
        
        return contact if contact.email or (contact.first_name and contact.last_name) else None
    
    def push_contact(self, contact: Contact) -> bool:
        """Push a contact to Square."""
        try:
            # Check if contact already exists in Square
            if 'square' in contact.source_ids:
                # Update existing customer
                self._update_customer(contact)
            else:
                # Create new customer
                self._create_customer(contact)
            return True
        except Exception as e:
            print(f"Error pushing contact to Square: {e}")
            return False
    
    def _create_customer(self, contact: Contact):
        """Create a new customer in Square."""
        body = self._contact_to_customer(contact)
        
        result = self.client.customers.create_customer(body=body)
        
        if result.is_success():
            customer = result.body.get('customer', {})
            contact.source_ids['square'] = customer.get('id')
        else:
            print(f"Error creating Square customer: {result.errors}")
    
    def _update_customer(self, contact: Contact):
        """Update an existing customer in Square."""
        customer_id = contact.source_ids['square']
        body = self._contact_to_customer(contact)
        
        result = self.client.customers.update_customer(
            customer_id=customer_id,
            body=body
        )
        
        if not result.is_success():
            print(f"Error updating Square customer: {result.errors}")
    
    def _contact_to_customer(self, contact: Contact) -> dict:
        """Convert Contact to Square customer object."""
        customer = {}
        
        # Name
        if contact.first_name:
            customer['given_name'] = contact.first_name
        if contact.last_name:
            customer['family_name'] = contact.last_name
        
        # Email
        if contact.email:
            customer['email_address'] = contact.email
        
        # Phone
        if contact.phone:
            customer['phone_number'] = contact.phone
        
        # Company
        if contact.company:
            customer['company_name'] = contact.company
        
        # Address
        if contact.addresses:
            addr = contact.addresses[0]  # Square supports one address
            customer['address'] = {
                'address_line_1': addr.get('street', ''),
                'locality': addr.get('city', ''),
                'administrative_district_level_1': addr.get('state', ''),
                'postal_code': addr.get('postal_code', ''),
                'country': addr.get('country', 'US')
            }
        
        # Notes
        if contact.notes:
            # Square API has a 500 character limit for customer notes
            customer['note'] = contact.notes[:500]
        
        return customer
