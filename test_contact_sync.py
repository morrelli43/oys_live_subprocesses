"""
Unit tests for contact model and sync engine.
"""
import unittest
from datetime import datetime
import os
import json

from contact_model import Contact, ContactStore
from sync_engine import SyncEngine


class TestContact(unittest.TestCase):
    """Test Contact class."""
    
    def test_contact_creation(self):
        """Test creating a contact."""
        contact = Contact('test_1')
        contact.first_name = 'John'
        contact.last_name = 'Doe'
        contact.email = 'john@example.com'
        
        self.assertEqual(contact.first_name, 'John')
        self.assertEqual(contact.last_name, 'Doe')
        self.assertEqual(contact.email, 'john@example.com')
    
    def test_contact_merge(self):
        """Test merging two contacts."""
        contact1 = Contact('c1')
        contact1.first_name = 'John'
        contact1.email = 'john@example.com'
        contact1.source_ids['google'] = 'g123'
        
        contact2 = Contact('c2')
        contact2.last_name = 'Doe'
        contact2.phone = '555-1234'
        contact2.source_ids['square'] = 's456'
        
        contact1.merge_with(contact2)
        
        # Check merged fields
        self.assertEqual(contact1.first_name, 'John')
        self.assertEqual(contact1.last_name, 'Doe')
        self.assertEqual(contact1.email, 'john@example.com')
        self.assertEqual(contact1.phone, '555-1234')
        
        # Check source IDs merged
        self.assertIn('google', contact1.source_ids)
        self.assertIn('square', contact1.source_ids)
    
    def test_contact_to_dict(self):
        """Test converting contact to dictionary."""
        contact = Contact('test_1')
        contact.first_name = 'Jane'
        contact.email = 'jane@example.com'
        
        data = contact.to_dict()
        
        self.assertEqual(data['contact_id'], 'test_1')
        self.assertEqual(data['first_name'], 'Jane')
        self.assertEqual(data['email'], 'jane@example.com')
    
    def test_contact_from_dict(self):
        """Test creating contact from dictionary."""
        data = {
            'contact_id': 'test_2',
            'first_name': 'Bob',
            'email': 'bob@example.com',
            'phone': '555-9999'
        }
        
        contact = Contact.from_dict(data)
        
        self.assertEqual(contact.contact_id, 'test_2')
        self.assertEqual(contact.first_name, 'Bob')
        self.assertEqual(contact.email, 'bob@example.com')
        self.assertEqual(contact.phone, '555-9999')


class TestContactStore(unittest.TestCase):
    """Test ContactStore class."""
    
    def setUp(self):
        """Set up test store."""
        self.store = ContactStore()
    
    def test_add_contact(self):
        """Test adding a contact to store."""
        contact = Contact()
        contact.first_name = 'Alice'
        contact.email = 'alice@example.com'
        
        contact_id = self.store.add_contact(contact)
        
        self.assertIsNotNone(contact_id)
        self.assertEqual(len(self.store.get_all_contacts()), 1)
    
    def test_duplicate_detection(self):
        """Test that duplicate emails are merged."""
        contact1 = Contact()
        contact1.first_name = 'Alice'
        contact1.email = 'alice@example.com'
        contact1.source_ids['google'] = 'g1'
        
        contact2 = Contact()
        contact2.last_name = 'Smith'
        contact2.email = 'alice@example.com'
        contact2.source_ids['square'] = 's1'
        
        id1 = self.store.add_contact(contact1)
        id2 = self.store.add_contact(contact2)
        
        # Should be same ID (merged)
        self.assertEqual(id1, id2)
        
        # Should only have one contact
        self.assertEqual(len(self.store.get_all_contacts()), 1)
        
        # Contact should have both source IDs
        merged = self.store.get_contact(id1)
        self.assertIn('google', merged.source_ids)
        self.assertIn('square', merged.source_ids)
    
    def test_get_contacts_by_source(self):
        """Test filtering contacts by source."""
        contact1 = Contact()
        contact1.email = 'user1@example.com'
        contact1.source_ids['google'] = 'g1'
        
        contact2 = Contact()
        contact2.email = 'user2@example.com'
        contact2.source_ids['square'] = 's1'
        
        self.store.add_contact(contact1)
        self.store.add_contact(contact2)
        
        google_contacts = self.store.get_contacts_by_source('google')
        square_contacts = self.store.get_contacts_by_source('square')
        
        self.assertEqual(len(google_contacts), 1)
        self.assertEqual(len(square_contacts), 1)


class TestSyncEngine(unittest.TestCase):
    """Test SyncEngine class."""
    
    def setUp(self):
        """Set up test engine."""
        self.store = ContactStore()
        self.engine = SyncEngine(self.store, state_file='test_sync_state.json')
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists('test_sync_state.json'):
            os.remove('test_sync_state.json')
    
    def test_register_connector(self):
        """Test registering a connector."""
        mock_connector = MockConnector()
        self.engine.register_connector('mock', mock_connector)
        
        self.assertIn('mock', self.engine.connectors)
    
    def test_merge_contacts(self):
        """Test merging contacts from multiple sources."""
        contacts_google = [
            self._create_contact('Alice', 'alice@example.com', 'google', 'g1')
        ]
        contacts_square = [
            self._create_contact('Bob', 'bob@example.com', 'square', 's1')
        ]
        
        source_contacts = {
            'google': contacts_google,
            'square': contacts_square
        }
        
        merged = self.engine.merge_contacts(source_contacts)
        
        self.assertEqual(len(merged), 2)
    
    def test_export_import(self):
        """Test exporting and importing contacts."""
        # Add some contacts
        contact = self._create_contact('Test', 'test@example.com', 'test', 't1')
        self.store.add_contact(contact)
        
        # Export
        export_file = 'test_export.json'
        self.engine.export_contacts(export_file)
        
        self.assertTrue(os.path.exists(export_file))
        
        # Clear store
        self.store.clear()
        self.assertEqual(len(self.store.get_all_contacts()), 0)
        
        # Import
        self.engine.import_contacts(export_file)
        
        self.assertEqual(len(self.store.get_all_contacts()), 1)
        
        # Clean up
        os.remove(export_file)
    
    def _create_contact(self, name, email, source, source_id):
        """Helper to create a test contact."""
        contact = Contact()
        contact.first_name = name
        contact.email = email
        contact.source_ids[source] = source_id
        return contact


class MockConnector:
    """Mock connector for testing."""
    
    def fetch_contacts(self):
        return []
    
    def push_contact(self, contact):
        return True


if __name__ == '__main__':
    unittest.main()
