"""Tests for engine/backup_to_oci.py — Oracle Object Storage backup (BACKUP-01)."""
from __future__ import annotations

import sys
import unittest.mock as mock

import pytest

from engine.backup_to_oci import backup_to_oracle, main


class TestBackupToOracle:
    def test_uploads_every_file_under_source_dir(self, tmp_path):
        source = tmp_path / "out"
        (source / "vol_index").mkdir(parents=True)
        (source / "surface_history").mkdir(parents=True)
        (source / "gex_snapshots.parquet").write_bytes(b"a")
        (source / "vol_index" / "VIX.parquet").write_bytes(b"b")
        (source / "surface_history" / "surface_SPY.parquet").write_bytes(b"c")

        mock_client = mock.Mock()
        with mock.patch("engine.backup_to_oci._s3_client", return_value=mock_client):
            backup_to_oracle("bucket", "ca-toronto-1", "ns", source)

        assert mock_client.upload_file.call_count == 3

    def test_key_uses_forward_slashes_relative_to_source_parent(self, tmp_path):
        source = tmp_path / "out"
        (source / "vol_index").mkdir(parents=True)
        (source / "vol_index" / "VIX.parquet").write_bytes(b"b")

        mock_client = mock.Mock()
        with mock.patch("engine.backup_to_oci._s3_client", return_value=mock_client):
            backup_to_oracle("bucket", "ca-toronto-1", "ns", source)

        call_args = mock_client.upload_file.call_args
        assert call_args[0][2] == "out/vol_index/VIX.parquet"

    def test_returns_upload_count(self, tmp_path):
        source = tmp_path / "out"
        source.mkdir(parents=True)
        (source / "a.parquet").write_bytes(b"1")
        (source / "b.parquet").write_bytes(b"2")

        mock_client = mock.Mock()
        with mock.patch("engine.backup_to_oci._s3_client", return_value=mock_client):
            count = backup_to_oracle("bucket", "ca-toronto-1", "ns", source)

        assert count == 2

    def test_empty_source_dir_uploads_nothing(self, tmp_path):
        source = tmp_path / "out"
        source.mkdir(parents=True)

        mock_client = mock.Mock()
        with mock.patch("engine.backup_to_oci._s3_client", return_value=mock_client):
            count = backup_to_oracle("bucket", "ca-toronto-1", "ns", source)

        assert count == 0
        mock_client.upload_file.assert_not_called()

    def test_upload_failure_propagates(self, tmp_path):
        source = tmp_path / "out"
        source.mkdir(parents=True)
        (source / "a.parquet").write_bytes(b"1")

        mock_client = mock.Mock()
        mock_client.upload_file.side_effect = RuntimeError("network down")
        with mock.patch("engine.backup_to_oci._s3_client", return_value=mock_client):
            with pytest.raises(RuntimeError):
                backup_to_oracle("bucket", "ca-toronto-1", "ns", source)

    def test_main_exits_nonzero_when_namespace_missing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OCI_NAMESPACE", raising=False)
        monkeypatch.setattr(
            sys, "argv",
            ["backup_to_oci", "--bucket", "x", "--region", "y", "--source", str(tmp_path)],
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
