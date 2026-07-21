"""
Restore out/ from an Oracle Cloud Object Storage backup (BACKUP-02).

Safety guarantee: refuses to overwrite a populated destination unless --force
is passed; corrupted downloads are surfaced as a hard failure, never used
silently.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import boto3
import pandas as pd


class RestoreSafetyError(RuntimeError):
    """Raised when dest already has files and neither --dry-run nor --force was passed (T-23-05)."""


class RestoreCorruptionError(RuntimeError):
    """Raised when a downloaded .parquet file fails its post-download integrity check (T-23-06)."""


def _s3_client(region: str, namespace: str):
    endpoint_url = f"https://{namespace}.compat.objectstorage.{region}.oraclecloud.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=os.environ["OCI_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["OCI_CUSTOMER_SECRET_KEY"],
        region_name=region,
    )


def list_backup_objects(client, bucket: str) -> list[dict]:
    return client.list_objects_v2(Bucket=bucket).get("Contents", [])


def restore_from_oci(
    bucket: str,
    region: str,
    namespace: str,
    dest: Path,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    existing_files = [p for p in dest.rglob("*") if p.is_file()] if dest.exists() else []
    if existing_files and not dry_run and not force:
        raise RestoreSafetyError(
            f"{dest} already contains {len(existing_files)} file(s). "
            "Re-run with --dry-run to preview, or --force to overwrite."
        )

    client = _s3_client(region, namespace)
    objects = list_backup_objects(client, bucket)

    if not objects:
        print("[restore_from_oci] no objects found in backup bucket.")
        return 0

    if dry_run:
        print(f"[restore_from_oci] DRY RUN — {len(objects)} object(s) would be downloaded:")
        for obj in objects:
            print(f"  {obj['Key']} ({obj.get('Size', '?')} bytes)")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    restored = 0
    for obj in objects:
        key = obj["Key"]
        rel = key.split("/", 1)[1] if key.startswith("out/") else key
        file_path = dest / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[restore_from_oci] downloading {key} ...")
        client.download_file(bucket, key, str(file_path))
        if file_path.suffix == ".parquet":
            try:
                pd.read_parquet(file_path)
            except Exception as exc:
                raise RestoreCorruptionError(
                    f"{file_path} failed integrity check after download: {exc}"
                ) from exc
        restored += 1

    print(f"[restore_from_oci] complete. {restored} file(s) restored to {dest}.")
    return restored


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore out/ from an Oracle Object Storage backup.")
    parser.add_argument("--bucket", default="vol-diagnostics-backup")
    parser.add_argument("--region", default="ca-toronto-1")
    parser.add_argument("--dest", type=Path, default=Path("./out"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    namespace = os.environ.get("OCI_NAMESPACE")
    if not namespace:
        print("[restore_from_oci] FAILED: OCI_NAMESPACE environment variable not set.", file=sys.stderr)
        sys.exit(1)

    try:
        restore_from_oci(
            args.bucket, args.region, namespace, args.dest,
            dry_run=args.dry_run, force=args.force,
        )
    except (RestoreSafetyError, RestoreCorruptionError) as exc:
        print(f"[restore_from_oci] ABORTED: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"[restore_from_oci] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
