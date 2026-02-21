from contact_model import Contact, ContactStore

def test_no_merge_on_empty_fields():
    store = ContactStore()
    
    # Contact A with empty email and phone space
    c1 = Contact()
    c1.first_name = "Adam"
    c1.last_name = "Sieff"
    c1.email = "   "
    c1.phone = " "
    store.add_contact(c1)
    
    # Contact B with no email and different phone space
    c2 = Contact()
    c2.first_name = "Marcus"
    c2.last_name = "Jones"
    c2.email = ""
    c2.phone = " ("
    store.add_contact(c2)
    
    contacts = store.get_all_contacts()
    if len(contacts) == 2:
        print("SUCCESS: Contacts were not merged.")
    else:
        print(f"FAILED: Contacts were merged. Expected 2, got {len(contacts)}")
        
if __name__ == "__main__":
    test_no_merge_on_empty_fields()
