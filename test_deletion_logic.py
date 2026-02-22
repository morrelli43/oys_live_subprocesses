"""
Tests for Square deletion → Google deletion propagation.
"""
import unittest
from unittest.mock import MagicMock, patch
from contact_model import Contact, ContactStore
from sync_engine import SyncEngine


class TestDeletionLogic(unittest.TestCase):

    def _make_contact(self, first, last, phone, square_id=None, google_id=None):
        """Helper to create a Contact with source IDs."""
        c = Contact()
        c.first_name = first
        c.last_name = last
        c.phone = phone
        if square_id:
            c.source_ids['square'] = square_id
        if google_id:
            c.source_ids['google'] = google_id
        return c

    def test_orphan_deleted_from_google(self):
        """A Google contact that was synced from Square but is no longer in Square gets deleted."""
        engine = SyncEngine()

        # Mock Google connector
        google_conn = MagicMock()
        orphan = self._make_contact("Deleted", "User", "0400000001",
                                    square_id="sq_gone", google_id="people/c111")
        google_conn.fetch_contacts.return_value = [orphan]
        google_conn._contact_to_person.return_value = {}
        google_conn.delete_contact.return_value = True

        # Mock Square connector - returns NO contacts (the contact was deleted)
        square_conn = MagicMock()
        square_conn.fetch_contacts.return_value = []
        square_conn._contact_to_customer.return_value = {}

        engine.register_connector('google', google_conn)
        engine.register_connector('square', square_conn)

        engine.sync_all()

        # The orphan should have been deleted from Google
        google_conn.delete_contact.assert_called_once_with("people/c111")

    def test_google_only_contact_not_deleted(self):
        """A Google contact without a Square source ID is left untouched."""
        engine = SyncEngine()

        # This contact only exists in Google (never synced from Square)
        google_only = self._make_contact("Google", "Only", "0400000002",
                                         google_id="people/c222")
        # No square_id set

        google_conn = MagicMock()
        google_conn.fetch_contacts.return_value = [google_only]
        google_conn._contact_to_person.return_value = {}
        google_conn.push_contact.return_value = True
        google_conn.delete_contact.return_value = True

        square_conn = MagicMock()
        square_conn.fetch_contacts.return_value = []
        square_conn._contact_to_customer.return_value = {}

        engine.register_connector('google', google_conn)
        engine.register_connector('square', square_conn)

        engine.sync_all()

        # delete_contact should NOT have been called
        google_conn.delete_contact.assert_not_called()

    def test_active_square_contact_not_deleted(self):
        """A contact that still exists in both Square and Google is NOT deleted."""
        engine = SyncEngine()

        sq_contact = self._make_contact("Active", "User", "0400000003",
                                        square_id="sq_active")
        goo_contact = self._make_contact("Active", "User", "0400000003",
                                         square_id="sq_active", google_id="people/c333")

        google_conn = MagicMock()
        google_conn.fetch_contacts.return_value = [goo_contact]
        google_conn._contact_to_person.return_value = {"names": []}
        google_conn.push_contact.return_value = True
        google_conn.delete_contact.return_value = True

        square_conn = MagicMock()
        square_conn.fetch_contacts.return_value = [sq_contact]
        square_conn._contact_to_customer.return_value = {"given_name": "Active"}
        square_conn.push_contact.return_value = True

        engine.register_connector('google', google_conn)
        engine.register_connector('square', square_conn)

        engine.sync_all()

        # delete_contact should NOT have been called
        google_conn.delete_contact.assert_not_called()

    def test_handle_square_deletion_webhook(self):
        """handle_square_deletion finds and deletes the matching Google contact."""
        engine = SyncEngine()

        matching = self._make_contact("Webhook", "Del", "0400000004",
                                      square_id="sq_webhook_del", google_id="people/c444")
        other = self._make_contact("Other", "Person", "0400000005",
                                   square_id="sq_other", google_id="people/c555")

        google_conn = MagicMock()
        google_conn.fetch_contacts.return_value = [matching, other]
        google_conn.delete_contact.return_value = True

        engine.register_connector('google', google_conn)

        engine.handle_square_deletion("sq_webhook_del")

        # Only the matching contact should be deleted
        google_conn.delete_contact.assert_called_once_with("people/c444")

    def test_handle_square_deletion_no_match(self):
        """handle_square_deletion does not delete anything if no match found."""
        engine = SyncEngine()

        unrelated = self._make_contact("Unrelated", "Person", "0400000006",
                                       square_id="sq_unrelated", google_id="people/c666")

        google_conn = MagicMock()
        google_conn.fetch_contacts.return_value = [unrelated]
        google_conn.delete_contact.return_value = True

        engine.register_connector('google', google_conn)

        engine.handle_square_deletion("sq_nonexistent")

        google_conn.delete_contact.assert_not_called()


if __name__ == '__main__':
    unittest.main()
