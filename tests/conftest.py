"""Common configuration shared by all tests in this directory."""

import os
import pytest
from pathlib import Path


@pytest.fixture
def script_source_dir():
    if "PROBS_MODULE_PATH" in os.environ:
        script_source_dir = os.environ["PROBS_MODULE_PATH"].split(os.pathsep)
    else:
        script_source_dir = None
    return script_source_dir
