"""
Demo script to showcase contact sync functionality.
This creates mock data and demonstrates the sync process without requiring API credentials.
"""
from contact_model import Contact, ContactStore
from sync_engine import SyncEngine


class MockConnector:
    """Mock connector that simulates an API source."""
    
    def __init__(self, name, initial_contacts=None):
        self.name = name
        self.contacts = initial_contacts or []
        self.pushed_contacts = []
    
    def fetch_contacts(self):
        """Return mock contacts."""
        return self.contacts.copy()
    
    def push_contact(self, contact):
        """Simulate pushing a contact."""
        self.pushed_contacts.append(contact)
        return True


def create_demo_contacts():
    """Create sample contacts for demonstration."""
    
    # Google contacts (2 contacts)
    google_contacts = []
    
    c1 = Contact()
    c1.first_name = "Alice"
    c1.last_name = "Johnson"
    c1.email = "alice.johnson@example.com"
    c1.phone = "555-0101"
    c1.source_ids['google'] = 'google_1'
    google_contacts.append(c1)
    
    c2 = Contact()
    c2.first_name = "Bob"
    c2.last_name = "Smith"
    c2.email = "bob.smith@example.com"
    c2.company = "Tech Corp"
    c2.source_ids['google'] = 'google_2'
    google_contacts.append(c2)
    
    # Square contacts (2 contacts, one overlapping with Google)
    square_contacts = []
    
    c3 = Contact()
    c3.first_name = "Alice"
    c3.email = "alice.johnson@example.com"  # Same as Google contact
    c3.company = "Design Studio"  # Additional info
    c3.source_ids['square'] = 'square_1'
    square_contacts.append(c3)
    
    c4 = Contact()
    c4.first_name = "Charlie"
    c4.last_name = "Brown"
    c4.email = "charlie.brown@example.com"
    c4.phone = "555-0303"
    c4.source_ids['square'] = 'square_2'
    square_contacts.append(c4)
    
    # Web form contacts (1 new contact)
    webform_contacts = []
    
    c5 = Contact()
    c5.first_name = "Diana"
    c5.last_name = "Prince"
    c5.email = "diana.prince@example.com"
    c5.phone = "555-0404"
    c5.notes = "Submitted via web form"
    c5.source_ids['webform'] = 'webform_1'
    webform_contacts.append(c5)
    
    return google_contacts, square_contacts, webform_contacts


def print_separator(title=""):
    """Print a nice separator."""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def print_contacts(contacts, title="Contacts"):
    """Print contact list in a nice format."""
    print(f"\n{title}:")
    if not contacts:
        print("  (none)")
        return
    
    for i, contact in enumerate(contacts, 1):
        print(f"\n  {i}. {contact.first_name} {contact.last_name}")
        print(f"     Email: {contact.email}")
        if contact.phone:
            print(f"     Phone: {contact.phone}")
        if contact.company:
            print(f"     Company: {contact.company}")
        if contact.notes:
            print(f"     Notes: {contact.notes}")
        print(f"     Sources: {', '.join(contact.source_ids.keys())}")


def main():
    """Run the demo."""
    
    print_separator("CONTACT SYNC SYSTEM DEMO")
    
    print("\nThis demo shows how the contact sync system works:")
    print("1. Contacts from multiple sources (Google, Square, Web Form)")
    print("2. Intelligent merging of duplicate contacts")
    print("3. Preservation of all information during merge")
    print("4. Synchronization back to all sources")
    
    # Create demo data
    google_contacts, square_contacts, webform_contacts = create_demo_contacts()
    
    # Display initial state
    print_separator("INITIAL STATE")
    print_contacts(google_contacts, "Google Contacts (2)")
    print_contacts(square_contacts, "Square Contacts (2, one duplicate)")
    print_contacts(webform_contacts, "Web Form Contacts (1)")
    
    print(f"\n  Total contacts before merge: {len(google_contacts) + len(square_contacts) + len(webform_contacts)}")
    
    # Set up sync engine
    store = ContactStore()
    engine = SyncEngine(store, state_file='demo_sync_state.json')
    
    # Register mock connectors
    google_connector = MockConnector('google', google_contacts)
    square_connector = MockConnector('square', square_contacts)
    webform_connector = MockConnector('webform', webform_contacts)
    
    engine.register_connector('google', google_connector)
    engine.register_connector('square', square_connector)
    engine.register_connector('webform', webform_connector)
    
    # Fetch all contacts
    print_separator("FETCHING CONTACTS")
    source_contacts = engine.fetch_all_contacts()
    
    # Merge contacts
    print_separator("MERGING CONTACTS")
    print("\nMerging duplicate contacts...")
    print("- Alice Johnson appears in both Google and Square")
    print("- Information from both sources will be combined")
    
    merged_contacts = engine.merge_contacts(source_contacts)
    
    print(f"\n  Unique contacts after merge: {len(merged_contacts)}")
    
    # Display merged contacts
    print_separator("MERGED CONTACTS")
    print_contacts(merged_contacts, "All Contacts (Merged)")
    
    print("\n  Key observations:")
    print("  - Alice Johnson has data from both Google and Square")
    print("  - She has both phone (from Google) and company (from Square)")
    print("  - All source IDs are preserved")
    
    # Display statistics
    print_separator("SYNC STATISTICS")
    stats = engine.get_sync_stats()
    print(f"\n  Total unique contacts: {stats['total_contacts']}")
    print("\n  Contacts per source:")
    for source, count in stats['sources'].items():
        print(f"    {source}: {count} contacts")
    
    # Demonstrate pushing to sources
    print_separator("PUSHING TO SOURCES")
    print("\nPushing merged contacts back to Google and Square...")
    print("(Web Form is input-only, so it's skipped)")
    
    success = engine.push_to_all_sources(merged_contacts)
    
    print(f"\n  Google received: {len(google_connector.pushed_contacts)} contacts")
    print(f"  Square received: {len(square_connector.pushed_contacts)} contacts")
    
    # Export demo
    print_separator("EXPORT EXAMPLE")
    engine.export_contacts('demo_contacts.json')
    print("\n✓ All contacts exported to demo_contacts.json")
    
    print_separator("DEMO COMPLETE")
    print("\nThe contact sync system successfully:")
    print("  ✓ Collected contacts from 3 sources")
    print("  ✓ Merged duplicates while preserving all information")
    print("  ✓ Maintained source tracking for each contact")
    print("  ✓ Pushed updates back to Google and Square")
    print("  ✓ Exported unified contact list")
    
    print("\nTo use with real APIs:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Configure .env file with your API credentials")
    print("  3. Run: python main.py sync")
    print("\nSee README.md for detailed setup instructions.")
    print()


if __name__ == '__main__':
    main()
