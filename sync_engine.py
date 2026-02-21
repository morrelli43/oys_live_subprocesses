"""
Sync engine for coordinating contact synchronization.
"""
from typing import List, Dict, Set
from datetime import datetime, timezone
import json
import os
import threading

from contact_model import Contact, ContactStore


class SyncEngine:
    """Coordinates contact synchronization across multiple sources."""
    
    def __init__(self, store: ContactStore, state_file: str = 'sync_state.json', contacts_file: str = 'contacts.json'):
        self.store = store
        self.state_file = state_file
        self.contacts_file = contacts_file
        self.connectors = {}
        self.last_sync_times = {}
        self.lock = threading.Lock()
        self.store.load_from_disk(self.contacts_file)
        self._load_state()
    
    def _load_state(self):
        """Load sync state from file."""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                self.last_sync_times = state.get('last_sync_times', {})
    
    def _save_state(self):
        """Save sync state to file."""
        state = {
            'last_sync_times': self.last_sync_times,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def register_connector(self, name: str, connector):
        """Register a contact source connector."""
        self.connectors[name] = connector
        if name not in self.last_sync_times:
            self.last_sync_times[name] = None
    
    def fetch_all_contacts(self) -> Dict[str, List[Contact]]:
        """Fetch contacts from all registered sources."""
        all_contacts = {}
        
        for name, connector in self.connectors.items():
            print(f"Fetching contacts from {name}...")
            try:
                contacts = connector.fetch_contacts()
                all_contacts[name] = contacts
                print(f"  Fetched {len(contacts)} contacts from {name}")
            except Exception as e:
                print(f"  Error fetching from {name}: {e}")
                all_contacts[name] = []
        
        return all_contacts
    
    def merge_contacts(self, source_contacts: Dict[str, List[Contact]]) -> List[Contact]:
        """Merge contacts from all sources into the store."""
        print("\nMerging contacts...")
        initial_count = len(self.store.get_all_contacts())
        
        for source_name, contacts in source_contacts.items():
            for contact in contacts:
                self.store.add_contact(contact)
        
        final_count = len(self.store.get_all_contacts())
        print(f"  Merged into {final_count} unique contacts (from {initial_count})")
        
        return self.store.get_all_contacts()

    def handle_deletions(self, source_contacts: Dict[str, List[Contact]]):
        """
        Detect contacts that have been deleted from a source and propagate deletion.
        A contact is considered deleted if:
        1. We have it in our persistent store with a source ID for a specific source.
        2. We successfully fetched contacts from that source.
        3. The contact is NOT in the fetched list.
        """
        print("\nChecking for deletions...")
        known_contacts = self.store.get_all_contacts()
        contacts_to_delete = []
        
        for contact in known_contacts:
            is_deleted = False
            
            for source_name, fetched_list in source_contacts.items():
                # Skip if we don't have an ID for this source (was never synced here)
                if source_name not in contact.source_ids:
                    continue
                    
                # Skip webform as it's not a source of truth for current state (it's a stream)
                if source_name == 'webform':
                    continue
                
                # Check if this source's ID is missing from fetched list
                source_id = contact.source_ids[source_name]
                found = False
                for fetched in fetched_list:
                    # Match by source ID (most reliable)
                    if fetched.source_ids.get(source_name) == source_id:
                        found = True
                        break
                        
                if not found:
                    print(f"  Contact {contact.first_name} {contact.last_name} missing from {source_name} (ID: {source_id}) - Marking for deletion")
                    is_deleted = True
                    break
            
            if is_deleted:
                contacts_to_delete.append(contact)
        
        # Process deletions
        if contacts_to_delete:
            print(f"  Found {len(contacts_to_delete)} contacts to delete.")
            self.propagate_deletions(contacts_to_delete)
        else:
            print("  No deletions detected.")

    def propagate_deletions(self, contacts: List[Contact]):
        """Delete contacts from all sources and local store."""
        for contact in contacts:
            print(f"  Propagating deletion for: {contact.first_name} {contact.last_name}")
            
            # Delete from all connected sources
            for name, connector in self.connectors.items():
                if name in contact.source_ids:
                    source_id = contact.source_ids[name]
                    if hasattr(connector, 'delete_contact'):
                        try:
                            connector.delete_contact(source_id)
                        except Exception as e:
                            print(f"    Error deleting from {name}: {e}")
            
            # Remove from local store
            # Currently ContactStore doesn't have remove, we need to rebuild or add remove.
            # Adding remove_contact to ContactStore would be better, but for now accessing dict directly
            if contact.contact_id in self.store.contacts:
                del self.store.contacts[contact.contact_id]
                
            # Clean up indexes
            if contact.email:
                clean_email = contact.email.strip().lower()
                if clean_email in self.store.email_index:
                    del self.store.email_index[clean_email]
            if contact.phone:
                clean_phone = ''.join(filter(str.isdigit, contact.phone))
                if clean_phone in self.store.phone_index:
                    del self.store.phone_index[clean_phone]
    
    def sync_all(self) -> bool:
        """Perform a full synchronization cycle. Thread-safe."""
        if not self.lock.acquire(blocking=False):
            print("Sync already in progress, skipping this trigger.")
            return False
            
        try:
            print("=" * 60)
            print("Starting synchronization cycle")
            print("=" * 60)
            
            # Fetch contacts from all sources
            source_contacts = self.fetch_all_contacts()
            
            # Check for deletions
            self.handle_deletions(source_contacts)

            # Merge all contacts
            merged_contacts = self.merge_contacts(source_contacts)
            
            # Push contacts back to all sources
            success = self.push_to_all_sources(merged_contacts)
            
            # Update sync times
            current_time = datetime.now(timezone.utc).isoformat()
            for name in self.connectors.keys():
                self.last_sync_times[name] = current_time
            
            self._save_state()
            self.store.save_to_disk(self.contacts_file)
            
            # Cleanup transitional sources (like webform queue)
            if success:
                for name, connector in self.connectors.items():
                    if hasattr(connector, 'clear_stored_contacts'):
                        try:
                            connector.clear_stored_contacts()
                        except Exception as e:
                            print(f"  Error clearing {name}: {e}")
            
            print("\n" + "=" * 60)
            print("Synchronization cycle completed")
            print("=" * 60)
            
            return success
        finally:
            self.lock.release()
    
        return success
    
    def push_to_all_sources(self, contacts: List[Contact]) -> bool:
        """Push merged contacts back to all sources."""
        print("\nPushing contacts to all sources...")
        success = True
        
        for source_name, connector in self.connectors.items():
            print(f"Pushing to {source_name}...")
            
            # Skip if connector doesn't support pushing (no push_contact method)
            if not hasattr(connector, 'push_contact'):
                print(f"  Skipping {source_name} (no push support)")
                continue
            
            pushed = 0
            errors = 0
            skipped = 0
            
            for contact in contacts:
                # Should we check if push is needed?
                # Ideally, connectors should handle "no change" efficiently or we check timestamps.
                # For now, we rely on connectors to be smart or just do it.
                # But let's log which contacts are being touched.
                try:
                    # In a real system, we might check if contact.source_ids[source_name] exists
                    # AND contact.last_modified > last_sync_time[source_name]
                    # But sync logic here is "always consistent", so we push.
                    if connector.push_contact(contact):
                        pushed += 1
                        # Verbose logging for debugging one specific contact if needed
                        # if contact.first_name == "Beth":
                        #     print(f"    Pushed Beth to {source_name}")
                    else:
                        errors += 1
                except Exception as e:
                    print(f"  Error pushing contact {contact.first_name} {contact.last_name}: {e}")
                    errors += 1
                    success = False
            
            print(f"  Pushed {pushed} contacts to {source_name}, {errors} errors")
        
        return success
    
    def get_sync_stats(self) -> Dict:
        """Get synchronization statistics."""
        stats = {
            'total_contacts': len(self.store.get_all_contacts()),
            'sources': {},
            'last_sync_times': self.last_sync_times
        }
        
        for name in self.connectors.keys():
            source_contacts = self.store.get_contacts_by_source(name)
            stats['sources'][name] = len(source_contacts)
        
        return stats
    
    def export_contacts(self, filename: str = 'contacts_export.json'):
        """Export all contacts to a JSON file."""
        contacts = self.store.get_all_contacts()
        data = [c.to_dict() for c in contacts]
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported {len(contacts)} contacts to {filename}")
    
    def import_contacts(self, filename: str):
        """Import contacts from a JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        count = 0
        for item in data:
            contact = Contact.from_dict(item)
            self.store.add_contact(contact)
            count += 1
        
        print(f"Imported {count} contacts from {filename}")
