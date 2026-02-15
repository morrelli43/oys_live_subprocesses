import unittest
from unittest.mock import MagicMock, patch
from contact_model import Contact, ContactStore
from sync_engine import SyncEngine

class TestDeletionLogic(unittest.TestCase):
    def setUp(self):
        self.store = ContactStore()
        self.engine = SyncEngine(self.store, state_file='test_state.json', contacts_file='test_contacts.json')
        
    def test_deletion_detection(self):
        # Setup: Store has a contact synced to 'sourceA'
        contact = Contact()
        contact.first_name = "To Be"
        contact.last_name = "Deleted"
        contact.email = "delete@me.com"
        contact.source_ids['sourceA'] = 'id_123'
        contact_id = self.store.add_contact(contact)
        
        # Mock connector for sourceA
        connectorA = MagicMock()
        # Fetch returns EMPTY list (simulating deletion in sourceA)
        connectorA.fetch_contacts.return_value = []
        connectorA.delete_contact = MagicMock()
        
        self.engine.register_connector('sourceA', connectorA)
        
        # Mock connector for sourceB (where it should be propagated)
        connectorB = MagicMock()
        connectorB.fetch_contacts.return_value = [] # Assume empty for simplicity
        self.engine.register_connector('sourceB', connectorB)
        
        # Run sync
        # We need to manually trigger handle_deletions logic or sync_all
        # Let's mock push_to_all_sources to avoid side effects
        self.engine.push_to_all_sources = MagicMock(return_value=True)
        self.engine._save_state = MagicMock()
        self.store.save_to_disk = MagicMock()
        
        # Run full sync
        self.engine.sync_all()
        
        # Verification
        # 1. Contact should be removed from store
        self.assertIsNone(self.store.get_contact(contact_id))
        
        # 2. Delete should be called on other connectors? 
        # Wait, the logic deletes from ALL connectors if deleted in ONE.
        # But only if it had an ID there.
        # Let's add sourceB ID to contact to test propagation
        contact.source_ids['sourceB'] = 'id_456'
        self.store.add_contact(contact) # Re-add
        
        # Reset mocks
        connectorA.delete_contact.reset_mock()
        connectorB.delete_contact = MagicMock()
        
        self.engine.sync_all()
        
        # Now check propagation
        connectorB.delete_contact.assert_called_with('id_456')
        connectorA.delete_contact.assert_called_with('id_123') # It tries to delete from sourceA too, which is fine/safe
        
if __name__ == '__main__':
    unittest.main()
