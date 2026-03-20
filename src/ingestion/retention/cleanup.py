"""Retention cleanup utilities.

Deletes old data cycles from S3 (or local) to keep only recent cycles.
"""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def cleanup_old_data(bucket: str, prefix: str, keep_cycles: int) -> List[str]:
    """Delete objects older than keep_cycles under a given prefix.

    This function uses s3fs for S3 access (anonymous or configured).
    For local paths, it deletes old directories.

    Args:
        bucket: S3 bucket name or empty string for local.
        prefix: Path prefix within the bucket.
        keep_cycles: Number of most recent cycles to keep.

    Returns:
        List[str]: Paths of deleted objects.
    """
    try:
        import s3fs

        fs = s3fs.S3FileSystem(anon=True)
        full_prefix = f"{bucket}/{prefix}" if bucket else prefix
        all_paths = fs.ls(full_prefix)
        # Sort by name assuming lexical order corresponds to chronological
        sorted_paths = sorted(all_paths)
        to_delete = (
            sorted_paths[:-keep_cycles] if keep_cycles < len(sorted_paths) else []
        )
        for path in to_delete:
            fs.rm(path, recursive=True)
        logger.info(f"Deleted {len(to_delete)} old objects from {full_prefix}")
        return to_delete
    except Exception as e:
        logger.error(f"Retention cleanup failed: {e}")
        # Fallback to local filesystem if bucket is empty
        if not bucket:
            try:
                dirs = [
                    d
                    for d in os.listdir(prefix)
                    if os.path.isdir(os.path.join(prefix, d))
                ]
                dirs.sort()
                to_del = dirs[:-keep_cycles] if keep_cycles < len(dirs) else []
                deleted = []
                for d in to_del:
                    full = os.path.join(prefix, d)
                    os.rmdir(full)
                    deleted.append(full)
                logger.info(
                    f"Deleted {len(deleted)} local old directories from {prefix}"
                )
                return deleted
            except Exception as ee:
                logger.error(f"Local cleanup error: {ee}")
        return []
