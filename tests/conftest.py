"""
Pytest configuration and fixtures for CTOA Test Suite
"""

import pytest
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)


@pytest.fixture
def project_root():
    """Fixture providing project root path"""
    return PROJECT_ROOT


@pytest.fixture
def config_path():
    """Fixture providing path to task state config"""
    return PROJECT_ROOT / "runtime" / "task-state.yaml"


@pytest.fixture
def sample_env():
    """Fixture providing sample environment variables"""
    return {
        "CTOA_VPS_HOST": "46.225.110.52",
        "CTOA_VPS_USER": "root",
        "CTOA_VPS_KEY_PATH": "/home/user/.ssh/ctoa_vps_ed25519",
    }


# Configure pytest
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as browser end-to-end smoke"
    )


# Test collection
def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Add timeout to all tests (30 seconds)
        if "timeout" not in item.keywords:
            item.add_marker(pytest.mark.timeout(30))
