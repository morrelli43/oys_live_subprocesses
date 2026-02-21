"""
Contact data model with strict phone-based merge capabilities.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import json
import os
import re


def normalize_phone(phone: str) -> str:
    """
    Universally normalize an Australian phone number to 04...
    Strips all non-digit characters. Converts 614... to 04...
    """
    if not phone:
        return ""
    
    # Strip all non-digits
    digits = ''.join(filter(str.isdigit, str(phone)))
    
    if digits.startswith("614") and len(digits) == 11:
        return "0" + digits[2:]
        
    if digits.startswith("0614") and len(digits) == 12:
         return "0" + digits[3:]
         
    return digits


def parse_single_line_address(address_str: str) -> dict:
    """Parse single-line AU addresses into components."""
    if not address_str:
        return {}
        
    address_str = address_str.strip()
    states_re = r'\b(VIC|NSW|QLD|ACT|TAS|WA|SA|NT|VICTORIA|NEW SOUTH WALES|QUEENSLAND|TASMANIA|WESTERN AUSTRALIA|SOUTH AUSTRALIA|NORTHERN TERRITORY)\b'
    state_map = {
        'VICTORIA': 'VIC', 'NEW SOUTH WALES': 'NSW', 'QUEENSLAND': 'QLD',
        'TASMANIA': 'TAS', 'WESTERN AUSTRALIA': 'WA', 'SOUTH AUSTRALIA': 'SA', 'NORTHERN TERRITORY': 'NT'
    }
    
    result = {}
    
    # Try comma separated: Street, Suburb State Postcode
    match1 = re.search(r'^(.*?),[\s]*([A-Za-z\s]+)[\s,]+' + states_re + r'[\s,]*(\d{4})\s*$', address_str, re.IGNORECASE)
    if match1:
        result['street'] = match1.group(1).strip()
        result['city'] = match1.group(2).strip()
        state = match1.group(3).upper()
        result['state'] = state_map.get(state, state)
        result['postal_code'] = match1.group(4).strip()
        result['country'] = 'AU'
        return result
        
    # Try greedy street no comma: Street Suburb State Postcode 
    match2 = re.search(r'^(.*)[\s]+([A-Za-z]+)[\s,]+' + states_re + r'[\s,]*(\d{4})\s*$', address_str, re.IGNORECASE)
    if match2:
        result['street'] = match2.group(1).strip()
        result['city'] = match2.group(2).strip()
        state = match2.group(3).upper()
        result['state'] = state_map.get(state, state)
        result['postal_code'] = match2.group(4).strip()
        result['country'] = 'AU'
        return result
        
    # Try Street Suburb Postcode (no state)
    match3 = re.search(r'^(.*?)[\s,]+([A-Za-z\s]+?)[\s,]+(\d{4})\s*$', address_str, re.IGNORECASE)
    if match3:
        result['street'] = match3.group(1).strip().rstrip(',')
        result['city'] = match3.group(2).strip().rstrip(',')
        result['postal_code'] = match3.group(3).strip()
        result['country'] = 'AU'
        return result
        
    # Return as-is if no obvious format 
    return {}


class Contact:
    """Represents a canonical contact synced between Square and Google."""
    
    def __init__(self, contact_id: str = None):
        self.contact_id = contact_id
        self.first_name: str = ""
        self.last_name: str = ""
        self.email: str = ""
        self.phone: str = ""
        self.company: str = ""
        self.notes: str = ""
        self.source_ids: Dict[str, str] = {}  # 'square' -> id, 'google' -> id
        self.last_modified: datetime = datetime.now(timezone.utc)
        self.addresses: List[Dict[str, str]] = []
        self.extra_fields: Dict[str, str] = {}
        
    @property
    def normalized_phone(self) -> str:
        """Returns the universally normalized phone number for matching."""
        return normalize_phone(self.phone)

    def merge_with(self, other: 'Contact', source_of_truth: str = 'square') -> 'Contact':
        """
        Merge this contact with another.
        If source_of_truth is specified, fields from that source explicitly clobber the other.
        """
        # Determine strict supremacy
        other_is_truth = (source_of_truth in other.source_ids)
        self_is_truth = (source_of_truth in self.source_ids)
        
        # If both are the source of truth (e.g. merging two square records?? shouldn't happen),
        # or neither is (e.g. memory webform + google fallback), fallback to timestamp
        if other_is_truth and not self_is_truth:
            other_wins = True
        elif self_is_truth and not other_is_truth:
            other_wins = False
        else:
            self_mod = self.last_modified if self.last_modified.tzinfo else self.last_modified.replace(tzinfo=timezone.utc)
            other_mod = other.last_modified if other.last_modified.tzinfo else other.last_modified.replace(tzinfo=timezone.utc)
            other_wins = (other_mod > self_mod)

        if other_wins:
            self.first_name = other.first_name or self.first_name
            self.last_name = other.last_name or self.last_name
            self.email = other.email or self.email
            self.phone = other.phone or self.phone
            self.company = other.company or self.company
            self.notes = other.notes or self.notes
            self.addresses = other.addresses or self.addresses
            
            # Explicitly overwrite extra fields from the winner
            for k, v in other.extra_fields.items():
                self.extra_fields[k] = v
        else:
            self.first_name = self.first_name or other.first_name
            self.last_name = self.last_name or other.last_name
            self.email = self.email or other.email
            self.phone = self.phone or other.phone
            self.company = self.company or other.company
            self.notes = self.notes or other.notes
            self.addresses = self.addresses or other.addresses
            
            for k, v in other.extra_fields.items():
                if k not in self.extra_fields or not self.extra_fields[k]:
                    self.extra_fields[k] = v

        # Source IDs are ALWAYS combined additively
        self.source_ids.update(other.source_ids)
        
        # Ensure only 1 address maximum and parse single lines
        if len(self.addresses) > 1:
            self.addresses = [self.addresses[0]]
            
        self.normalize_addresses()
            
        return self

    def normalize_addresses(self):
        """Refactor single line addresses into explicit components."""
        for addr in self.addresses:
            street = addr.get('street', '').strip()
            city = addr.get('city', '').strip()
            postcode = addr.get('postal_code', '').strip()
            
            # If we only have a street and no city/postcode, it's likely a single-line address
            if street and not city and not postcode:
                parsed = parse_single_line_address(street)
                if parsed:
                    # Update with structured components
                    addr.update(parsed)

    def to_dict(self) -> Dict:
        return {
            'contact_id': self.contact_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'company': self.company,
            'notes': self.notes,
            'source_ids': self.source_ids,
            'last_modified': self.last_modified.isoformat(),
            'addresses': self.addresses,
            'extra_fields': self.extra_fields
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Contact':
        contact = Contact(data.get('contact_id'))
        contact.first_name = data.get('first_name', "")
        contact.last_name = data.get('last_name', "")
        contact.email = data.get('email', "")
        contact.phone = data.get('phone', "")
        contact.company = data.get('company', "")
        contact.notes = data.get('notes', "")
        contact.source_ids = data.get('source_ids', {})
        contact.addresses = data.get('addresses', [])
        contact.extra_fields = data.get('extra_fields', {})
        
        if 'last_modified' in data:
            dt = datetime.fromisoformat(data['last_modified'])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            contact.last_modified = dt
            
        contact.normalize_addresses()
        return contact

    def __repr__(self):
        return f"Contact({self.first_name} {self.last_name}, {self.phone})"


class ContactStore:
    """In-memory canonical storage, explicitly matching only on normalized phone numbers."""
    
    def __init__(self):
        self.contacts: Dict[str, Contact] = {}
        self.phone_index: Dict[str, str] = {}  # canonical 04... phone -> contact_id
        
    def add_contact(self, contact: Contact, source_of_truth: str = 'square') -> str:
        """Add or merge a contact by strict phone match."""
        # Enforce defaults for AU
        for addr in contact.addresses:
            if not addr.get('state'):
                addr['state'] = 'Victoria'
            if not addr.get('country'):
                addr['country'] = 'AU'

        existing_id = None
        clean_phone = contact.normalized_phone
        
        # ONLY deduplicate if there is a valid phone number
        if clean_phone and clean_phone in self.phone_index:
            existing_id = self.phone_index[clean_phone]
            
        if existing_id:
            # Merge into the existing contact
            self.contacts[existing_id].merge_with(contact, source_of_truth=source_of_truth)
            self._update_indexes(self.contacts[existing_id])
            return existing_id
            
        # New Contact, generate ID
        if not contact.contact_id:
            contact.contact_id = f"contact_{len(self.contacts) + 1}"
            
        self.contacts[contact.contact_id] = contact
        self._update_indexes(contact)
        return contact.contact_id

    def _update_indexes(self, contact: Contact):
        """Update lookup indexes using ONLY normalized phone numbers."""
        clean_phone = contact.normalized_phone
        if clean_phone:
            self.phone_index[clean_phone] = contact.contact_id

    def get_all_contacts(self) -> List[Contact]:
        return list(self.contacts.values())
        
    def get_contact_by_phone(self, phone: str) -> Optional[Contact]:
        clean = normalize_phone(phone)
        if clean and clean in self.phone_index:
            return self.contacts[self.phone_index[clean]]
        return None

    def clear(self):
        self.contacts.clear()
        self.phone_index.clear()
