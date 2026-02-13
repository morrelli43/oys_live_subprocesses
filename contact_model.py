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
        self.extra_fields.update(other.extra_fields)
        
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
    
    def __repr__(self):
        return f"Contact({self.first_name} {self.last_name}, {self.email})"


class ContactStore:
    """In-memory storage for contacts with deduplication."""
    
    def __init__(self):
        self.contacts: Dict[str, Contact] = {}
        self.email_index: Dict[str, str] = {}  # email -> contact_id
    
    def add_contact(self, contact: Contact) -> str:
        """Add or merge a contact. Returns the contact_id."""
        # Try to find existing contact by email
        if contact.email and contact.email in self.email_index:
            existing_id = self.email_index[contact.email]
            self.contacts[existing_id].merge_with(contact)
            return existing_id
        
        # Generate ID if needed
        if not contact.contact_id:
            contact.contact_id = f"contact_{len(self.contacts) + 1}"
        
        self.contacts[contact.contact_id] = contact
        
        # Update email index
        if contact.email:
            self.email_index[contact.email] = contact.contact_id
        
        return contact.contact_id
    
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
