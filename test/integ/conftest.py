# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
from pathlib import Path

import pytest


@pytest.fixture
def keyshot_location() -> Path:
    return Path(os.environ["KEYSHOT_EXECUTABLE"])


@pytest.fixture
def script_location() -> Path:
    return Path(__file__).parent / "test_scripts"
