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
        
        # Ensure custom attribute definitions exist
        self._ensure_custom_attribute_definitions()
        
    def _ensure_custom_attribute_definitions(self):
        """Ensure custom attribute definitions exist for escooter fields."""
        # This is a simplified check. In production, you'd cache these IDs.
        # We need to map our keys (escooter1) to Square's Attribute Definition IDs.
        self.attribute_keys = {}
        
        try:
            # List existing definitions
            result = self.client.customer_custom_attributes.list_customer_custom_attribute_definitions()
            
            existing_keys = {}
            if result.is_success():
                for definition in result.body.get('custom_attribute_definitions', []):
                    existing_keys[definition.get('key')] = definition.get('id')
            
            # Create missing definitions
            for key in ['escooter1', 'escooter2', 'escooter3']:
                if key in existing_keys:
                    self.attribute_keys[key] = existing_keys[key]
                else:
                    print(f"Creating Square custom attribute definition for {key}...")
                    body = {
                        "custom_attribute_definition": {
                            "key": key,
                            "name": key.capitalize(),
                            "description": f"Custom field for {key}",
                            "visibility": "VISIBILITY_READ_WRITE_VALUES",
                            "schema": {
                                "ref": f"https://developer-production.squareup.com/CustomAttributeDefinition/{key}",
                                "type": "String" # Simplified type
                            }
                        }
                    }
                    create_result = self.client.customer_custom_attributes.create_customer_custom_attribute_definition(body=body)
                    
                    if create_result.is_success():
                        new_def = create_result.body.get('custom_attribute_definition')
                        self.attribute_keys[key] = new_def.get('id')
                        print(f"  Created {key} with ID {new_def.get('id')}")
                    else:
                        print(f"  Error creating {key}: {create_result.errors}")
                        
        except Exception as e:
            print(f"Warning: Could not ensure Square custom attributes: {e}")
            print("  Make sure your token has CUSTOMERS_WRITE and CUSTOMERS_READ permissions.")
    
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
                'street2': address.get('address_line_2', ''),
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
            
        # Extract Custom Attributes (requires separate API call usually, or expanding the object)
        # Note: list_customers usually returns sparse objects. We might need to fetch individual customer
        # to get custom attributes, or they might be included if permissions allow.
        # For now, we'll try to read from the 'custom_attributes' field if present.
        custom_attrs = customer.get('custom_attributes', {})
        # If it's a list (some endpoints), convert to dict. If it's a dict (others), use as is.
        # Square API structure for custom attributes can be complex.
        # Assuming we just get them or need to fetch them. 
        # For this implementation, we will assume they are not present in list_customers default response
        # and would need a separate fetch. To keep it simple and efficient, we will skip *reading* 
        # them in the bulk list for now, unless requested. 
        
        # However, if we do have them (e.g. from retrieve_customer), map them:
        if custom_attrs:
             for key, value_obj in custom_attrs.items():
                 # value_obj might be {'value': '...'} or just the value depending on API version/endpoint
                 val = value_obj.get('value') if isinstance(value_obj, dict) else value_obj
                 # We need to map Definition ID back to Key if possible, OR if the key is the definition key.
                 # This is tricky without a reverse lookup map.
                 # For now, we will assume we might not get them easily in bulk sync without extra calls.
                 pass

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
                'address_line_2': addr.get('street2', ''),
                'locality': addr.get('city', ''),
                'administrative_district_level_1': addr.get('state', ''),
                'postal_code': addr.get('postal_code', ''),
                'country': addr.get('country', 'US')
            }
        
        # Notes
        if contact.notes:
            customer['note'] = contact.notes[:500]
            
        # Custom Attributes
        # We need to map our keys (escooter1) to the Attribute Definition keys or IDs.
        # Using the key directly is supported in some endpoints.
        custom_attributes = {}
        for key, value in contact.extra_fields.items():
            if key in ['escooter1', 'escooter2', 'escooter3']:
                # Square expects: {"key": "escooter1", "value": "Model Name"}
                # But creating a customer with custom attributes requires a specific structure map
                # key -> value.
                custom_attributes[key] = {'value': str(value)}
        
        if custom_attributes:
            customer['custom_attributes'] = custom_attributes
        
        return customer
