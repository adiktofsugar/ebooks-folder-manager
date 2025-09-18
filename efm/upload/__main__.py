#!/usr/bin/env python3
"""
Upload static site to Cloudflare Workers

This script uploads a static site directory to Cloudflare Workers,
making it available as a Workers site with global CDN distribution.
"""

import argparse
import os
from pathlib import Path
import sys
from typing import cast
from . import upload_to_cloudflare_worker


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "site_dir", type=Path, help="Path to the static site directory to upload"
    )
    parser.add_argument(
        "--account-id",
        help="Cloudflare account ID (can also be set via CLOUDFLARE_ACCOUNT_ID env var)",
    )
    parser.add_argument(
        "--api-token",
        help="Cloudflare API token (can also be set via CLOUDFLARE_API_TOKEN env var)",
    )
    parser.add_argument(
        "--script-name", default="efm", help="Name of the Worker script (default: efm)"
    )

    args = parser.parse_args()
    site_dir = cast(Path, args.site_dir)
    account_id = cast(str | None, args.account_id) or os.environ.get(
        "CLOUDFLARE_ACCOUNT_ID"
    )
    api_token = cast(str | None, args.api_token) or os.environ.get(
        "CLOUDFLARE_API_TOKEN"
    )
    script_name = cast(str, args.script_name)

    if not site_dir.exists():
        print(f"Error: Site directory '{site_dir}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not site_dir.is_dir():
        print(f"Error: '{site_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    if not account_id:
        print(
            "Error: Cloudflare account ID is required (use --account-id or set CLOUDFLARE_ACCOUNT_ID)",
            file=sys.stderr,
        )
        sys.exit(1)

    if not api_token:
        print(
            "Error: Cloudflare API token is required (use --api-token or set CLOUDFLARE_API_TOKEN)",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        upload_to_cloudflare_worker(
            site_dir,
            account_id=account_id,
            api_token=api_token,
            script_name=script_name,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
