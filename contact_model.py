"""
Contact data model with merge capabilities.
"""
from typing import Dict, List, Optional, Set
from datetime import datetime


class Contact:
    """Represents a contact with information from multiple sources."""
    
    def __init__(self, contact_id: str = None):
        self.contact_id = contact_id
        self.first_name: Optional[str] = None
        self.last_name: Optional[str] = None
        self.email: Optional[str] = None
        self.phone: Optional[str] = None
        self.company: Optional[str] = None
        self.notes: Optional[str] = None
        self.source_ids: Dict[str, str] = {}  # source_name -> source_id
        self.last_modified: datetime = datetime.now()
        self.addresses: List[Dict[str, str]] = []
        self.extra_fields: Dict[str, str] = {}
    
    def merge_with(self, other: 'Contact') -> 'Contact':
        """
        Merge this contact with another, keeping as much information as possible.
        Prefers non-None values and combines source_ids.
        """
        # Prefer non-empty values
        self.first_name = self.first_name or other.first_name
        self.last_name = self.last_name or other.last_name
        self.email = self.email or other.email
        self.phone = self.phone or other.phone
        self.company = self.company or other.company
        
        # Combine notes
        if other.notes and other.notes not in (self.notes or ''):
            self.notes = f"{self.notes}\n{other.notes}" if self.notes else other.notes
        
        # Merge source IDs
        self.source_ids.update(other.source_ids)
        
        # Merge addresses (avoiding duplicates)
        for addr in other.addresses:
            if addr not in self.addresses:
                self.addresses.append(addr)
        
        # Merge extra fields
        # specific logic for escooter fields to fill sequentially
        escooter_values = []
        
        # Collect existing values
        for key in ['escooter1', 'escooter2', 'escooter3']:
            if self.extra_fields.get(key):
                escooter_values.append(self.extra_fields[key])
        
        # Collect new values
        for key in ['escooter1', 'escooter2', 'escooter3']:
            if other.extra_fields.get(key):
                val = other.extra_fields[key]
                if val not in escooter_values:
                    escooter_values.append(val)
        
        # Update other extra fields (non-escooter)
        for k, v in other.extra_fields.items():
            if not k.startswith('escooter'):
                self.extra_fields[k] = v
                
        # Redistribute escooter values
        for i, val in enumerate(escooter_values[:3]): # Max 3
            self.extra_fields[f'escooter{i+1}'] = val
            
        # Clear any remaining higher indices if count reduced (unlikely in additive merge but good practice)
        for i in range(len(escooter_values), 3):
             if f'escooter{i+1}' in self.extra_fields:
                 del self.extra_fields[f'escooter{i+1}']
        
        # Update timestamp
        if other.last_modified > self.last_modified:
            self.last_modified = other.last_modified
        
        return self
    
    def to_dict(self) -> Dict:
        """Convert contact to dictionary format."""
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
        """Create contact from dictionary format."""
        contact = Contact(data.get('contact_id'))
        contact.first_name = data.get('first_name')
        contact.last_name = data.get('last_name')
        contact.email = data.get('email')
        contact.phone = data.get('phone')
        contact.company = data.get('company')
        contact.notes = data.get('notes')
        contact.source_ids = data.get('source_ids', {})
        contact.addresses = data.get('addresses', [])
        contact.extra_fields = data.get('extra_fields', {})
        
        if 'last_modified' in data:
            contact.last_modified = datetime.fromisoformat(data['last_modified'])
        
        return contact
    
    def to_vcard(self) -> str:
        """Convert contact to vCard string format (v3.0)."""
        lines = ['BEGIN:VCARD', 'VERSION:3.0']
        
        # Name
        n_parts = [
            self.last_name or '',
            self.first_name or '',
            '', '', ''
        ]
        lines.append(f"N:{';'.join(n_parts)}")
        
        fn = f"{self.first_name or ''} {self.last_name or ''}".strip()
        if fn:
            lines.append(f"FN:{fn}")
        
        # Email
        if self.email:
            lines.append(f"EMAIL;TYPE=INTERNET:{self.email}")
        
        # Phone
        if self.phone:
            lines.append(f"TEL;TYPE=CELL:{self.phone}")
            
        # Company
        if self.company:
            lines.append(f"ORG:{self.company}")
            
        # Address (vCard 3.0 ADR expects: PO Box; Ext Address; Street; City; Region; Postal Code; Country)
        for addr in self.addresses:
            # Map street2 to Extended Address (or append to street if preferred, but ADR has a slot for it)
            # Standard: [PO Box]; [Extended Address]; [Street Address]; [Locality]; [Region]; [Postal Code]; [Country]
            street1 = addr.get('street', '')
            street2 = addr.get('street2', '')
            
            adr_parts = [
                '',
                street2,  # Extended Address (Apt/Suite)
                street1,  # Street Address
                addr.get('city', ''),
                addr.get('state', ''),
                addr.get('postal_code', ''),
                addr.get('country', '')
            ]
            lines.append(f"ADR;TYPE=HOME:{';'.join(adr_parts)}")
            
        # Notes
        if self.notes:
            lines.append(f"NOTE:{self.notes}")
            
        # Custom Fields (X-ESCOOTER1, etc.)
        for key, value in self.extra_fields.items():
            if key.startswith('escooter'):
                # Normalize key to uppercase X- format
                field_name = f"X-{key.upper()}"
                lines.append(f"{field_name}:{value}")
                
        lines.append('END:VCARD')
        return '\n'.join(lines)

    def __repr__(self):
        return f"Contact({self.first_name} {self.last_name}, {self.email})"


class ContactStore:
    """In-memory storage for contacts with deduplication."""
    
    def __init__(self):
        self.contacts: Dict[str, Contact] = {}
        self.email_index: Dict[str, str] = {}  # email -> contact_id
        self.phone_index: Dict[str, str] = {}  # phone -> contact_id
    
    def add_contact(self, contact: Contact) -> str:
        """Add or merge a contact. Returns the contact_id."""
        # Enforce defaults for State and Country if missing
        for addr in contact.addresses:
            if not addr.get('state'):
                addr['state'] = 'Victoria'
            if not addr.get('country'):
                addr['country'] = 'Australia'

        existing_id = None
        
        # Try to find existing contact by email
        if contact.email and contact.email in self.email_index:
            existing_id = self.email_index[contact.email]
            
        # Try to find existing contact by phone if not found by email
        if not existing_id and contact.phone and contact.phone in self.phone_index:
            existing_id = self.phone_index[contact.phone]
            
        if existing_id:
            self.contacts[existing_id].merge_with(contact)
            # Update indexes with merged data (in case missing fields were filled)
            self._update_indexes(self.contacts[existing_id])
            return existing_id
        
        # Generate ID if needed
        if not contact.contact_id:
            contact.contact_id = f"contact_{len(self.contacts) + 1}"
        
        self.contacts[contact.contact_id] = contact
        self._update_indexes(contact)
        
        return contact.contact_id
    
    def _update_indexes(self, contact: Contact):
        """Update lookup indexes for a contact."""
        if contact.email:
            self.email_index[contact.email] = contact.contact_id
        if contact.phone:
            self.phone_index[contact.phone] = contact.contact_id
    
    def get_contact(self, contact_id: str) -> Optional[Contact]:
        """Get a contact by ID."""
        return self.contacts.get(contact_id)
    
    def get_all_contacts(self) -> List[Contact]:
        """Get all contacts."""
        return list(self.contacts.values())
    
    def get_contacts_by_source(self, source_name: str) -> List[Contact]:
        """Get all contacts from a specific source."""
        return [c for c in self.contacts.values() if source_name in c.source_ids]
    
    def clear(self):
        """Clear all contacts."""
        self.contacts.clear()
        self.email_index.clear()
        self.phone_index.clear()
