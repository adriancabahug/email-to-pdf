import sys
sys.path.insert(0, ".")

from datetime import datetime
from src.outlook_session_manager import OutlookSessionManager

session = OutlookSessionManager()
session.connect()
namespace = session._namespace

print("=== Accounts in Outlook ===")
for i, account in enumerate(namespace.Folders, 1):
    print(f"{i}. {account.Name}")
    # Count total emails in this account
    total = 0
    try:
        for folder in account.Folders:
            try:
                total += folder.Items.Count
            except:
                pass
    except:
        pass
    print(f"   Total items: {total}")

print("\n=== Searching for 'Soulbaila' across ALL accounts ===")
found = []
for account in namespace.Folders:
    for folder in account.Folders:
        try:
            items = folder.Items
            for msg in items:
                subject = str(getattr(msg, "Subject", "")).lower()
                if "soulbaila" in subject:
                    found.append({
                        "account": account.Name,
                        "folder": folder.Name,
                        "subject": msg.Subject,
                        "sender": msg.SenderName,
                        "received": msg.ReceivedTime
                    })
        except Exception as e:
            pass

print(f"Found {len(found)} matches")
for f in found[:5]:
    print(f"  Account: {f['account']} | Folder: {f['folder']}")
    print(f"    Subject: {f['subject']}")
    print(f"    From: {f['sender']} | Date: {f['received']}")

session.disconnect()