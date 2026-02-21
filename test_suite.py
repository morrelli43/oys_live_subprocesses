import unittest
from contact_model import Contact, ContactStore, normalize_phone

class TestContactModelV2(unittest.TestCase):
    
    def test_normalize_phone(self):
        # Australian formats
        self.assertEqual(normalize_phone("+61412345678"), "0412345678")
        self.assertEqual(normalize_phone("0412 345 678"), "0412345678")
        self.assertEqual(normalize_phone("61412345678"), "0412345678")
        self.assertEqual(normalize_phone("(04) 1234 5678"), "0412345678")
        self.assertEqual(normalize_phone("061412345678"), "0412345678")
        
        # Trash strings
        self.assertEqual(normalize_phone(""), "")
        self.assertEqual(normalize_phone("  "), "")
        self.assertEqual(normalize_phone("N/A"), "")
        
    def test_square_wins_conflict(self):
        c1 = Contact()
        c1.first_name = "Adam"
        c1.phone = "0412345678"
        c1.source_ids['square'] = "sq_123"
        c1.company = "SquareCorp"
        
        c2 = Contact()
        c2.first_name = "Adam2" # Different name in Google
        c2.phone = "0412345678"
        c2.source_ids['google'] = "go_456"
        c2.company = "GoogleCorp"
        
        c1.merge_with(c2, source_of_truth='square')
        
        # Since c1 is Square (the explicit source of truth), it should reject c2's properties
        # when merging, even if c2 is newer timestamp
        self.assertEqual(c1.first_name, "Adam")
        self.assertEqual(c1.company, "SquareCorp")
        self.assertIn('square', c1.source_ids)
        self.assertIn('google', c1.source_ids)
        
    def test_google_yields_to_square(self):
        # What if Google initiates the merge but yields to Square?
        go_contact = Contact()
        go_contact.first_name = "GoogleName"
        go_contact.source_ids['google'] = 'go_111'
        
        sq_contact = Contact()
        sq_contact.first_name = "SquareName"
        sq_contact.source_ids['square'] = 'sq_111'
        
        go_contact.merge_with(sq_contact, source_of_truth='square')
        self.assertEqual(go_contact.first_name, "SquareName")
        
    def test_store_deduplication(self):
        store = ContactStore()
        
        c1 = Contact()
        c1.phone = "+61 412 345 678"
        c1.first_name = "First"
        store.add_contact(c1)
        
        c2 = Contact()
        c2.phone = "0412345678"
        c2.last_name = "Last"
        store.add_contact(c2)
        
        contacts = store.get_all_contacts()
        self.assertEqual(len(contacts), 1)
        
        merged = contacts[0]
        self.assertEqual(merged.first_name, "First")
        self.assertEqual(merged.last_name, "Last")
        self.assertEqual(merged.normalized_phone, "0412345678")

    def test_no_empty_phone_crashes(self):
        store = ContactStore()
        c1 = Contact()
        c1.email = "test@test.com"
        c1.phone = "  "
        store.add_contact(c1)
        
        c2 = Contact()
        c2.email = "other@test.com"
        c2.phone = ""
        store.add_contact(c2)
        
        # They should NOT merge simply because both have empty phones
        self.assertEqual(len(store.get_all_contacts()), 2)
        
    def test_parse_address(self):
        c1 = Contact()
        c1.addresses.append({'street': '123 Fake Street, Melbourne VIC 3000'})
        c1.normalize_addresses()
        addr = c1.addresses[0]
        self.assertEqual(addr['street'], '123 Fake Street')
        self.assertEqual(addr['city'], 'Melbourne')
        self.assertEqual(addr['state'], 'VIC')
        self.assertEqual(addr['postal_code'], '3000')
        
        c2 = Contact()
        c2.addresses.append({'street': '100 Just Street, 3000'})
        c2.normalize_addresses()
        addr2 = c2.addresses[0]
        self.assertEqual(addr2['street'], '100')
        self.assertEqual(addr2['city'], 'Just Street')
        self.assertEqual(addr2['postal_code'], '3000')

if __name__ == '__main__':
    unittest.main()
