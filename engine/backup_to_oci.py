"""
Backup out/ to Oracle Cloud Object Storage via its S3-compatible API (BACKUP-01).

Never logs credentials. Reads OCI_ACCESS_KEY_ID / OCI_CUSTOMER_SECRET_KEY from
environment variables only — never hardcoded, never passed as a CLI argument.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import boto3


def _s3_client(region: str, namespace: str):
    endpoint_url = f"https://{namespace}.compat.objectstorage.{region}.oraclecloud.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=os.environ["OCI_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["OCI_CUSTOMER_SECRET_KEY"],
        region_name=region,
    )


def backup_to_oracle(bucket: str, region: str, namespace: str, source_dir: Path) -> int:
    """Upload every file under source_dir to bucket, keyed by path relative to source_dir's parent."""
    client = _s3_client(region, namespace)
    uploaded = 0
    for file_path in sorted(source_dir.rglob("*")):
        if not file_path.is_file():
            continue
        key = str(file_path.relative_to(source_dir.parent)).replace(os.sep, "/")
        print(f"[backup_to_oci] uploading {key} ...")
        client.upload_file(str(file_path), bucket, key)
        uploaded += 1
    print(f"[backup_to_oci] complete. {uploaded} file(s) uploaded to {bucket}.")
    return uploaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up out/ to Oracle Object Storage.")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()

    namespace = os.environ.get("OCI_NAMESPACE")
    if not namespace:
        print("[backup_to_oci] FAILED: OCI_NAMESPACE environment variable not set.", file=sys.stderr)
        sys.exit(1)

    if not args.source.exists():
        print(f"[backup_to_oci] FAILED: source directory not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    try:
        backup_to_oracle(args.bucket, args.region, namespace, args.source)
    except Exception as exc:
        print(f"[backup_to_oci] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
