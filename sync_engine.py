"""
Sync engine for coordinating contact synchronization in V2 architecture.
Always considers Square as the primary source of truth.
"""
from typing import List, Dict
import threading

from contact_model import Contact, ContactStore

class SyncEngine:
    """Coordinates contact synchronization across multiple sources in memory."""
    
    def __init__(self):
        self.store = ContactStore()
        self.connectors = {}
        self.lock = threading.Lock()
    
    def register_connector(self, name: str, connector):
        """Register a contact source connector."""
        self.connectors[name] = connector
    
    def process_incoming_webhook(self, data: dict, source_name: str = 'webform'):
        """
        Process an incoming webhook/webform and instantly push to destinations.
        """
        if not self.lock.acquire(blocking=False):
            print("Sync in progress, delaying webhook processing...")
            self.lock.acquire() # block until done
            
        try:
            print(f"Processing incoming {source_name} data...")
            contact = Contact()
            contact.first_name = data.get('first_name', '')
            contact.last_name = data.get('last_name') or data.get('surname', '')
            contact.phone = data.get('phone') or data.get('number', '')
            contact.email = data.get('email', '')
            contact.company = data.get('company', '')
            contact.notes = data.get('notes') or data.get('issue', '')
            
            # Map address
            address = data.get('address') or data.get('address_line_1', '')
            suburb = data.get('suburb', '')
            state = data.get('state', 'Victoria')
            postcode = data.get('postcode', '')
            country = data.get('country', 'AU')
            
            if address or suburb or postcode:
                contact.addresses.append({
                    'street': address,
                    'city': suburb,
                    'state': state,
                    'postal_code': postcode,
                    'country': country
                })
                
            # Escooters
            escooter_val = data.get('escooter1') or data.get('escooter')
            if not escooter_val:
                scooter_name = data.get('scooter_name') or data.get('make', '')
                scooter_model = data.get('scooter_model') or data.get('model', '')
                if scooter_name or scooter_model:
                    escooter_val = f"{scooter_name} {scooter_model}".strip()
            
            if escooter_val:
                contact.extra_fields['escooter1'] = escooter_val
            
            for i in range(2, 4):
                key = f'escooter{i}'
                if data.get(key):
                    contact.extra_fields[key] = data[key]
                    
            # Set memory ID
            import time
            contact.source_ids[source_name] = str(time.time())
            
            # Drop the webform directly into the store so it has memory presence
            # then instantly push to Square.
            if not contact.normalized_phone:
                print("WARNING: Webhook payload missing parseable phone, dropping.")
                return False
                
            self.store.add_contact(contact, source_of_truth=source_name)
            
            # Instant Push to Square and Google
            for target_name, connector in self.connectors.items():
                if hasattr(connector, 'push_contact'):
                    print(f"Instantly pushing webhook contact to {target_name}...")
                    connector.push_contact(contact)
                    
            return True
        finally:
            self.lock.release()

    def sync_all(self) -> bool:
        """Perform a full synchronization cycle explicitly weighting Square."""
        if not self.lock.acquire(blocking=False):
            print("Sync already in progress, skipping this trigger.")
            return False
            
        try:
            print("=" * 60)
            print("Starting V2 synchronization cycle")
            print("=" * 60)
            
            self.store.clear()
            
            # 1. Fetch Square (Source of Truth)
            if 'square' in self.connectors:
                print("Fetching contacts from Square (Source of Truth)...")
                try:
                    square_contacts = self.connectors['square'].fetch_contacts()
                    for c in square_contacts:
                        self.store.add_contact(c, source_of_truth='square')
                    print(f"  Loaded {len(square_contacts)} Square contacts.")
                except Exception as e:
                    print(f"  Error fetching from Square: {e}")
                    
            # 2. Fetch Google Contacts 
            if 'google' in self.connectors:
                print("Fetching contacts from Google...")
                try:
                    google_contacts = self.connectors['google'].fetch_contacts()
                    for c in google_contacts:
                        # Add them, but specify 'google' which yields to 'square' on conflict
                        self.store.add_contact(c, source_of_truth='google')
                    print(f"  Loaded {len(google_contacts)} Google contacts.")
                except Exception as e:
                    print(f"  Error fetching from Google: {e}")
            
            # 3. Push Unified Data Back to ALL Sources
            unified_contacts = self.store.get_all_contacts()
            success = self.push_to_all_sources(unified_contacts)
            
            print("\n" + "=" * 60)
            print(f"V2 Synchronization cycle completed. {len(unified_contacts)} unique contacts.")
            print("=" * 60)
            return success
            
        finally:
            self.lock.release()
    
    def push_to_all_sources(self, contacts: List[Contact]) -> bool:
        print("\nPushing normalized contacts back to all destinations...")
        success = True
        
        for source_name, connector in self.connectors.items():
            if not hasattr(connector, 'push_contact'):
                continue
            
            print(f"Pushing to {source_name}...")
            pushed = 0
            errors = 0
            
            for contact in contacts:
                # Do not push contacts that have absolutely no phone number
                if not contact.normalized_phone:
                    continue
                    
                try:
                    if connector.push_contact(contact):
                        pushed += 1
                    else:
                        errors += 1
                except Exception as e:
                    print(f"  Error pushing contact {contact.first_name} {contact.last_name}: {e}")
                    errors += 1
                    success = False
            
            print(f"  Pushed {pushed} contacts to {source_name}, {errors} errors")
        
        return success
