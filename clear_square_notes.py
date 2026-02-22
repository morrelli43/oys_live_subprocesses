"""
One-off script to clear the native 'note' (aka 'Other') field
from ALL Square customers. Uses Square SDK v44+.
"""
import os
from square import Square

access_token = os.getenv('SQUARE_ACCESS_TOKEN')
if not access_token:
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('SQUARE_ACCESS_TOKEN='):
                    access_token = line.split('=', 1)[1].strip().strip('"').strip("'")

if not access_token:
    print("ERROR: SQUARE_ACCESS_TOKEN not found. Set it as an env var or in .env")
    exit(1)

client = Square(token=access_token)

# Fetch all customers via the v44 pager
customers = []
print("Fetching all Square customers...")
for customer in client.customers.list():
    customers.append(customer)

print(f"Found {len(customers)} customers.\n")

# Clear the 'note' field for each customer that has one
cleared = 0
skipped = 0

for cust in customers:
    name = f"{cust.given_name or ''} {cust.family_name or ''}".strip() or cust.id
    note = cust.note
    
    if note:
        print(f"  Clearing note for {name}: \"{note[:60]}{'...' if len(note) > 60 else ''}\"")
        try:
            client.customers.update(customer_id=cust.id, note='')
            cleared += 1
        except Exception as e:
            print(f"    ERROR: {e}")
    else:
        skipped += 1

print(f"\nDone! Cleared {cleared} notes. Skipped {skipped} customers (already blank).")
