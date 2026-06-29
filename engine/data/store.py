"""
Shared parquet-store I/O helpers.

The daily snapshot stores (gex_snapshots, surface_history, oi_history,
surface_evolution, vol_index) hold irreplaceable CBOE history — there is no
upstream archive to re-fetch from. The read-modify-write pattern those stores
use overwrites the whole file in place, so an interrupted write (sleep, power
loss, disk hiccup on an unattended WakeToRun box) can truncate the file and
take the entire accumulated history with it.

`atomic_to_parquet` writes to a temp file in the same directory and then
`os.replace`s it over the target — atomic on Windows and POSIX for a same-volume
move, so a crash mid-write leaves the previous good file untouched.
"""
from __future__ import annotations

import os
import pathlib
import tempfile

import pandas as pd


def atomic_to_parquet(df: pd.DataFrame, path: pathlib.Path | str) -> None:
    """Write df to path atomically (temp file + os.replace). Never truncates an
    existing store on an interrupted write."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".parquet", dir=str(path.parent))
    os.close(fd)
    try:
        df.to_parquet(tmp, index=False)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
