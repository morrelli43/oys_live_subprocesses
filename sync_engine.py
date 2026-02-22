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
            
            # Instant Push to Square only.
            # The Square webhook will fire back and trigger a full sync to Google.
            if 'square' in self.connectors and hasattr(self.connectors['square'], 'push_contact'):
                print(f"Pushing webhook contact to Square...")
                self.connectors['square'].push_contact(contact)
                    
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
            print("Starting v2.3.0 synchronization cycle")
            print("=" * 60)
            
            self.store.clear()
            
            # 1. Fetch Square (Source of Truth)
            square_phones = set()  # Track phones fetched from Square for orphan detection
            if 'square' in self.connectors:
                print("Fetching contacts from Square (Source of Truth)...")
                try:
                    square_contacts = self.connectors['square'].fetch_contacts()
                    for c in square_contacts:
                        # Snaphot the exact payload Square gave us
                        c._original_square_payload = self.connectors['square']._contact_to_customer(c)
                        c._original_square_attrs = {k: v for k, v in c.extra_fields.items() if k in ['escooter1', 'escooter2', 'escooter3']}
                        self.store.add_contact(c, source_of_truth='square')
                        if c.normalized_phone:
                            square_phones.add(c.normalized_phone)
                    print(f"  Loaded {len(square_contacts)} Square contacts.")
                except Exception as e:
                    print(f"  Error fetching from Square: {e}")
                    
            # 2. Fetch Google Contacts 
            google_contacts = []
            if 'google' in self.connectors:
                print("Fetching contacts from Google...")
                try:
                    google_contacts = self.connectors['google'].fetch_contacts()
                    for c in google_contacts:
                        # Snapshot the exact payload Google gave us
                        c._original_google_payload = self.connectors['google']._contact_to_person(c)
                        # Add them, enforcing Square as the persistent source of truth
                        added_id = self.store.add_contact(c, source_of_truth='square')
                        
                        # Store the google payload on the unified canonical object so we can dirty-check later
                        self.store.contacts[added_id]._original_google_payload = c._original_google_payload
                    print(f"  Loaded {len(google_contacts)} Google contacts.")
                except Exception as e:
                    print(f"  Error fetching from Google: {e}")
            
            # 2.5. Orphan Detection: delete Google contacts no longer in Square
            if 'google' in self.connectors and 'square' in self.connectors:
                self._delete_google_orphans(google_contacts, square_phones)
            
            # 3. Push Unified Data Back to ALL Sources
            unified_contacts = self.store.get_all_contacts()
            success = self.push_to_all_sources(unified_contacts)
            
            print("\n" + "=" * 60)
            print(f"v2.3.0 Synchronization cycle completed. {len(unified_contacts)} unique contacts.")
            print("=" * 60)
            return success
            
        finally:
            self.lock.release()
    
    def _delete_google_orphans(self, google_contacts: List[Contact], square_phones: set):
        """Delete Google contacts that no longer exist in Square.
        
        Only deletes contacts that have a Square source ID, proving they
        were previously synced from Square. Google-only contacts are safe.
        
        Args:
            google_contacts: Contacts fetched from Google this cycle.
            square_phones: Set of normalized phone numbers fetched from Square.
        """
        
        deleted_count = 0
        for gc in google_contacts:
            google_resource = gc.source_ids.get('google')
            had_square_id = 'square' in gc.source_ids
            phone = gc.normalized_phone
            
            # Safety: only delete if the contact was previously synced from Square
            if not had_square_id:
                continue
            
            # If this contact's phone is NOT in any current Square contact, it's an orphan
            if phone and phone not in square_phones:
                print(f"  Orphan detected: {gc.first_name} {gc.last_name} ({phone}) - deleting from Google")
                try:
                    if self.connectors['google'].delete_contact(google_resource):
                        deleted_count += 1
                        # Also remove from in-memory store
                        to_remove = [cid for cid, c in self.store.contacts.items() 
                                     if c.normalized_phone == phone]
                        for cid in to_remove:
                            del self.store.contacts[cid]
                except Exception as e:
                    print(f"  Error deleting orphan from Google: {e}")
        
        if deleted_count:
            print(f"  Deleted {deleted_count} orphaned Google contact(s).")

    def handle_square_deletion(self, square_customer_id: str):
        """Handle a customer.deleted webhook from Square.
        
        Finds the matching Google contact and deletes it.
        """
        if 'google' not in self.connectors:
            print("  No Google connector registered, skipping deletion propagation.")
            return
        
        with self.lock:
            print(f"\nHandling Square deletion for customer ID: {square_customer_id}")
            
            try:
                google_contacts = self.connectors['google'].fetch_contacts()
            except Exception as e:
                print(f"  Error fetching Google contacts for deletion: {e}")
                return
            
            # Find the Google contact that was synced from this Square customer
            for gc in google_contacts:
                if gc.source_ids.get('square') == square_customer_id:
                    google_resource = gc.source_ids.get('google')
                    if google_resource:
                        print(f"  Found matching Google contact: {gc.first_name} {gc.last_name}")
                        try:
                            self.connectors['google'].delete_contact(google_resource)
                        except Exception as e:
                            print(f"  Error deleting from Google: {e}")
                    return
            
            print(f"  No matching Google contact found for Square customer {square_customer_id}")

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
                    
                # Intelligent dirty checking to prevent infinite loops and API burning
                try:
                    if source_name == 'square':
                        new_sq_payload = connector._contact_to_customer(contact)
                        new_sq_attrs = {k: v for k, v in contact.extra_fields.items() if k in ['escooter1', 'escooter2', 'escooter3']}
                        
                        orig_sq_payload = getattr(contact, '_original_square_payload', None)
                        orig_sq_attrs = getattr(contact, '_original_square_attrs', None)
                        
                        if orig_sq_payload is not None and orig_sq_payload == new_sq_payload and orig_sq_attrs == new_sq_attrs:
                            # print(f"  Skipping {contact.first_name}... no changes for Square.")
                            continue
                            
                    elif source_name == 'google':
                        new_go_payload = connector._contact_to_person(contact)
                        orig_go_payload = getattr(contact, '_original_google_payload', None)
                        
                        if orig_go_payload is not None and orig_go_payload == new_go_payload:
                            # print(f"  Skipping {contact.first_name}... no changes for Google.")
                            continue
                except Exception as e:
                    print(f"  Warning during diff check: {e}")

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
