"""Tests for engine/restore_from_oci.py — Oracle Object Storage restore (BACKUP-02)."""
from __future__ import annotations

import unittest.mock as mock

import pandas as pd
import pytest

from engine.restore_from_oci import (
    restore_from_oci,
    list_backup_objects,
    RestoreSafetyError,
    RestoreCorruptionError,
)


class TestRestoreFromOci:
    def test_dry_run_lists_without_downloading(self, tmp_path):
        dest = tmp_path / "out"
        mock_client = mock.Mock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "out/vol_index/VIX.parquet", "Size": 123}]
        }
        with mock.patch("engine.restore_from_oci._s3_client", return_value=mock_client):
            count = restore_from_oci("bucket", "ca-toronto-1", "ns", dest, dry_run=True)

        mock_client.download_file.assert_not_called()
        assert count == 0

    def test_refuses_to_overwrite_populated_dest_without_force(self, tmp_path):
        dest = tmp_path / "out"
        dest.mkdir(parents=True)
        (dest / "existing.parquet").write_bytes(b"x")

        mock_client = mock.Mock()
        with mock.patch("engine.restore_from_oci._s3_client", return_value=mock_client):
            with pytest.raises(RestoreSafetyError):
                restore_from_oci("bucket", "ca-toronto-1", "ns", dest, dry_run=False, force=False)

        mock_client.download_file.assert_not_called()

    def test_force_allows_overwrite_of_populated_dest(self, tmp_path):
        dest = tmp_path / "out"
        dest.mkdir(parents=True)
        (dest / "existing.parquet").write_bytes(b"x")

        mock_client = mock.Mock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "out/vol_index/VIX.parquet", "Size": 10}]
        }

        def fake_download(bucket, key, path):
            with open(path, "wb") as f:
                pd.DataFrame({"a": [1]}).to_parquet(f)

        mock_client.download_file.side_effect = fake_download

        with mock.patch("engine.restore_from_oci._s3_client", return_value=mock_client):
            count = restore_from_oci("bucket", "ca-toronto-1", "ns", dest, dry_run=False, force=True)

        mock_client.download_file.assert_called_once()
        assert count == 1
        assert (dest / "vol_index" / "VIX.parquet").exists()

    def test_empty_bucket_returns_zero(self, tmp_path):
        dest = tmp_path / "out"
        mock_client = mock.Mock()
        mock_client.list_objects_v2.return_value = {}
        with mock.patch("engine.restore_from_oci._s3_client", return_value=mock_client):
            count = restore_from_oci("bucket", "ca-toronto-1", "ns", dest, dry_run=False, force=False)

        mock_client.download_file.assert_not_called()
        assert count == 0

    def test_corrupted_parquet_raises_restore_corruption_error(self, tmp_path):
        dest = tmp_path / "out"
        mock_client = mock.Mock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "out/gex_snapshots.parquet", "Size": 5}]
        }

        def fake_download(bucket, key, path):
            with open(path, "wb") as f:
                f.write(b"not a parquet file")

        mock_client.download_file.side_effect = fake_download

        with mock.patch("engine.restore_from_oci._s3_client", return_value=mock_client):
            with pytest.raises(RestoreCorruptionError):
                restore_from_oci("bucket", "ca-toronto-1", "ns", dest, dry_run=False, force=False)

    def test_key_prefix_stripped_for_non_out_prefixed_keys(self, tmp_path):
        dest = tmp_path / "out"
        mock_client = mock.Mock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "misc/notes.txt", "Size": 3}]
        }

        def fake_download(bucket, key, path):
            with open(path, "wb") as f:
                f.write(b"hi")

        mock_client.download_file.side_effect = fake_download

        with mock.patch("engine.restore_from_oci._s3_client", return_value=mock_client):
            count = restore_from_oci("bucket", "ca-toronto-1", "ns", dest, dry_run=False, force=False)

        assert count == 1
        assert (dest / "misc" / "notes.txt").exists()


class TestListBackupObjects:
    def test_returns_contents_list(self):
        mock_client = mock.Mock()
        mock_client.list_objects_v2.return_value = {"Contents": [{"Key": "a"}]}
        result = list_backup_objects(mock_client, "bucket")
        assert result == [{"Key": "a"}]

    def test_returns_empty_list_when_no_contents(self):
        mock_client = mock.Mock()
        mock_client.list_objects_v2.return_value = {}
        result = list_backup_objects(mock_client, "bucket")
        assert result == []
