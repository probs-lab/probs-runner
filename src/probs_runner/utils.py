from typing import Union
import time
import sys
import os
import shutil
import gzip
from tempfile import NamedTemporaryFile
import logging


logger = logging.getLogger(__name__)


def is_gzipped(filename: Union[os.PathLike, str]):
    """Test whether the file is gzipped, based on its filename"""
    # XXX simple test but fast and good enough?
    return str(filename).endswith(".gz")


def prepare_file_for_rdfox(
    source: Union[os.PathLike, str], target: Union[os.PathLike, str]
):
    """Ensure file is compatible with RDFox missing decompression.

    On Linux/Mac, RDFox with gzip decompress files ending with `.gz`, but on
    Windows this does nothing. This function applies gzip decompression manually
    if needed, returning the path to the decompressed temporary file. Otherwise
    it returns the original path unchanged.
    """

    # Files for RDFox should never be compressed on Windows. They should be
    # compressed on other platforms if the target filename looks like a
    # compressed file.
    #
    # Assume the source file is correctly compressed or not based on its
    # filename.
    source_is_compressed = is_gzipped(source)
    want_target_compressed = sys.platform != "win32" and is_gzipped(target)

    if source_is_compressed != want_target_compressed:
        f = NamedTemporaryFile(delete=False)
        f.close()
        logger.debug(
            "Fixing compression: %r -> %r (source_is_compressed=%s, want_target_compressed=%s)",
            source,
            f.name,
            source_is_compressed,
            want_target_compressed,
        )
        copy_maybe_gzipped(source, f.name, source_is_compressed, want_target_compressed)
        return f.name

    else:
        # The source file is already ok, avoid unnecessary copy to temporary file
        logger.debug("No compression fix needed for %s", source)
        return source


def wait_for_file(filename: Union[os.PathLike, str], timeout: float):
    """Poll for up to `timeout` seconds until `filename` is not empty."""
    start_time = time.time()
    while True:
        if os.path.isfile(filename) and os.path.getsize(filename) > 0:
            print(filename, time.time() - start_time)
            return True
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            return False
        time.sleep(0.01)


def copy_from_rdfox(
    source: Union[os.PathLike, str], target: Union[os.PathLike, str], timeout=None
):
    """Copy an output file, working around RDFox optional compression.

    On Linux/Mac, RDFox with gzip compress files ending with `.gz`, but on
    Windows this does nothing. This function applies gzip compression manually
    if needed.

    If `timeout` is given, wait for up to `timeout` seconds for the file size to
    be greater than zero; this is needed because RDFox can exit before it has
    finished writing compressed data to the file.

    """

    if timeout is not None:
        wait_for_file(source, timeout)

    # Files from RDFox are not compressed on Windows, despite the extension. On
    # other platforms, determine based on whether the target filename looks like
    # a compressed file.
    #
    # Decide whether the target file should be compressed based on the filename.
    source_is_compressed = sys.platform != "win32" and is_gzipped(source)
    want_target_compressed = is_gzipped(target)
    copy_maybe_gzipped(source, target, source_is_compressed, want_target_compressed)


def copy_maybe_gzipped(
    source: Union[os.PathLike, str],
    target: Union[os.PathLike, str],
    source_is_compressed: bool,
    want_target_compressed: bool,
):
    """Copy an input file, ensuring desired state of compression."""

    if want_target_compressed and not source_is_compressed:
        # Need to compress
        with open(source, "rb") as fin, gzip.open(target, "wb") as fout:
            shutil.copyfileobj(fin, fout)

    elif not want_target_compressed and source_is_compressed:
        # Need to decompress
        with gzip.open(source, "rb") as fin, open(target, "wb") as fout:
            shutil.copyfileobj(fin, fout)

    else:
        # Just copy
        shutil.copy(source, target)
