"""
Sync engine for coordinating contact synchronization.
"""
from typing import List, Dict, Set
from datetime import datetime
import json
import os

from contact_model import Contact, ContactStore


class SyncEngine:
    """Coordinates contact synchronization across multiple sources."""
    
    def __init__(self, store: ContactStore, state_file: str = 'sync_state.json'):
        self.store = store
        self.state_file = state_file
        self.connectors = {}
        self.last_sync_times = {}
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
            'last_updated': datetime.now().isoformat()
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
    
    def sync_all(self) -> bool:
        """Perform a full synchronization cycle."""
        print("=" * 60)
        print("Starting synchronization cycle")
        print("=" * 60)
        
        # Fetch contacts from all sources
        source_contacts = self.fetch_all_contacts()
        
        # Merge all contacts
        merged_contacts = self.merge_contacts(source_contacts)
        
        # Push contacts back to all sources
        success = self.push_to_all_sources(merged_contacts)
        
        # Update sync times
        current_time = datetime.now().isoformat()
        for name in self.connectors.keys():
            self.last_sync_times[name] = current_time
        
        self._save_state()
        
        print("\n" + "=" * 60)
        print("Synchronization cycle completed")
        print("=" * 60)
        
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
            
            for contact in contacts:
                try:
                    if connector.push_contact(contact):
                        pushed += 1
                    else:
                        errors += 1
                except Exception as e:
                    print(f"  Error pushing contact: {e}")
                    errors += 1
                    success = False
            
            print(f"  Pushed {pushed} contacts, {errors} errors")
        
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
