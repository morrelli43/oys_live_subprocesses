#!/usr/bin/env python3
"""
Simple script to locally generate a new Google Contacts token.json
Run this on your Mac with your `credentials.json` available.
"""
import os
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/contacts']

def generate_token(cred_file='credentials.json', token_file='token.json'):
    if not os.path.exists(cred_file):
        print(f"ERROR: {cred_file} not found!")
        print("Please download it from your Google Cloud Console and place it here.")
        return

    # Delete expired token if it exists
    if os.path.exists(token_file):
        print(f"Removing old expired {token_file}...")
        os.remove(token_file)

    print("Opening browser to authenticate with Google...")
    flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save credentials
    with open(token_file, 'w') as token:
        token.write(creds.to_json())
    
    print(f"\n✅ Successfully generated new {token_file}!")
    print("\nYou can now upload this file to your Raspberry Pi at:")
    print("  ~/dockerhub/permadata/oys_contacts/env_files/token.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Refresh Google OAuth Token')
    parser.add_argument('--credentials', default='env_files/credentials.json', help='Path to your Google credentials file')
    parser.add_argument('--token', default='env_files/token.json', help='Output path for the generated token file')
    args = parser.parse_args()
    
    generate_token(args.credentials, args.token)
