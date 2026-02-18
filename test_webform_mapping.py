
import unittest
from webform_connector import WebFormConnector
from contact_model import Contact

class TestWebFormMapping(unittest.TestCase):
    def setUp(self):
        self.connector = WebFormConnector(storage_file='test_webform_contacts.json')
        # Clear any existing test data
        self.connector.clear_stored_contacts()

    def test_postcode_processing_and_mapping(self):
        # 1. Simulate form data submission
        test_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'suburb': 'Melbourne',
            'postcode': '3000',
            'phone': '0400000000'
        }
        
        # Process the data
        self.connector._process_contact_data(test_data)
        
        # 2. Verify it's stored correctly in internal list
        self.assertEqual(len(self.connector.stored_contacts), 1)
        self.assertEqual(self.connector.stored_contacts[0]['postcode'], '3000')
        
        # 3. Verify fetch_contacts maps it correctly to Contact model
        contacts = self.connector.fetch_contacts()
        self.assertEqual(len(contacts), 1)
        contact = contacts[0]
        
        self.assertEqual(len(contact.addresses), 1)
        self.assertEqual(contact.addresses[0]['city'], 'Melbourne')
        self.assertEqual(contact.addresses[0]['postal_code'], '3000')

    def test_address_processing_and_mapping(self):
        # 1. Simulate form data submission with address
        test_data = {
            'first_name': 'Address',
            'last_name': 'Tester',
            'address': '123 Test St',
            'suburb': 'Testville',
            'postcode': '9999',
            'phone': '0411111111'
        }
        
        # Process the data
        self.connector._process_contact_data(test_data)
        
        # 2. Verify it's stored correctly in internal list
        self.assertEqual(len(self.connector.stored_contacts), 1)
        self.assertEqual(self.connector.stored_contacts[0]['address'], '123 Test St')
        
        # 3. Verify fetch_contacts maps it correctly to Contact model
        contacts = self.connector.fetch_contacts()
        self.assertEqual(len(contacts), 1)
        contact = contacts[0]
        
        self.assertEqual(len(contact.addresses), 1)
        self.assertEqual(contact.addresses[0]['street'], '123 Test St')
        self.assertEqual(contact.addresses[0]['city'], 'Testville')

    def tearDown(self):
        import os
        if os.path.exists('test_webform_contacts.json'):
            os.remove('test_webform_contacts.json')

if __name__ == '__main__':
    unittest.main()
