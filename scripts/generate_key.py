#!/usr/bin/env python3
"""
Key Generator - Generates license keys for the email-to-pdf tool.

Usage:
    python scripts/generate_key.py --days 90

Output:
    Prints the generated key and the Cloudflare Worker config entry.
    The config entry should be added to cloudflare-worker/index.js KEYS object.
"""

import argparse
import secrets
import string
from datetime import datetime, timedelta


def generate_key() -> str:
    """Generate a segmented alphanumeric key: XXXXXX-XXXXXX-XXXXXX"""
    alphabet = string.ascii_uppercase + string.digits
    segments = []
    for _ in range(3):
        segment = "".join(secrets.choice(alphabet) for _ in range(6))
        segments.append(segment)
    return "-".join(segments)


def main():
    parser = argparse.ArgumentParser(description="Generate license keys for email-to-pdf tool")
    parser.add_argument("--days", type=int, default=30, help="Number of days until key expires (default: 30)")
    args = parser.parse_args()

    key = generate_key()
    expires = datetime.now() + timedelta(days=args.days)
    expires_str = expires.strftime("%Y-%m-%d")

    print(f"Generated key: {key}")
    print(f"Expires: {expires_str} ({args.days} days from now)")
    print()
    print("Add this entry to cloudflare-worker/index.js KEYS object:")
    print(f'  "{key}": {{ "expires": "{expires_str}" }}')


if __name__ == "__main__":
    main()
