import unittest
from contact_model import Contact
from sync_engine import SyncEngine

class TestCustomID(unittest.TestCase):
    def test_id_generation(self):
        engine = SyncEngine()
        contact = Contact()
        contact.phone = "0412345678" # Necessary for store matching
        
        # Test generation helper
        engine._ensure_custom_id(contact)
        self.assertTrue(contact.custom_id.startswith("cst-"))
        self.assertEqual(len(contact.custom_id), 13) # cst- + 9 digits
        
    def test_webhook_id_assignment(self):
        engine = SyncEngine()
        data = {
            'first_name': 'Test',
            'phone': '0412345678'
        }
        engine.process_incoming_webhook(data)
        
        # Check that the contact in the store has a custom ID
        stored_contact = engine.store.get_contact_by_phone("0412345678")
        self.assertIsNotNone(stored_contact.custom_id)
        self.assertTrue(stored_contact.custom_id.startswith("cst-"))

    def test_push_id_assignment(self):
        engine = SyncEngine()
        contact = Contact()
        contact.first_name = "Bulk"
        contact.phone = "0487654321"
        engine.store.add_contact(contact)
        
        # Push to all sources should trigger ID generation for all
        engine.push_to_all_sources([contact])
        self.assertIsNotNone(contact.custom_id)
        self.assertTrue(contact.custom_id.startswith("cst-"))

if __name__ == '__main__':
    unittest.main()
