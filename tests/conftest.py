import pytest
from pathlib import Path
import logging

@pytest.fixture
def pdf_path():
    # Provide the path to a sample PDF file for testing
    return Path("/home/lankovas/nomad-distro-dev/Report MRO008.pdf")

@pytest.fixture
def logger():
    """Provide a logger instance for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("test_logger")