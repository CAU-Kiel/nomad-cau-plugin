"""Wrapper normalizer for Michaela schema.

This module re-exports the existing CaP normalizer as `MichaelaNormalizer`.
It keeps the implementation centralized while allowing clearer naming for the
Michaela schema package.
"""

from .CaP_experiments_normalizer import CaPNormalizer


class MichaelaNormalizer(CaPNormalizer):
    """Alias/subclass for CaPNormalizer used by the Michaela schema."""

    pass


# Backwards-compatible API: expose the commonly used static methods
process_xrd_file = CaPNormalizer.process_xrd_file
process_ir_file = CaPNormalizer.process_ir_file
process_dls_files = CaPNormalizer.process_dls_files
