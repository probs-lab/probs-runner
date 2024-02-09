"""Common configuration shared by all tests in this directory."""

import os
import pytest
from pathlib import Path


@pytest.fixture
def script_source_dir():
    script_source_dir = None
    return script_source_dir
