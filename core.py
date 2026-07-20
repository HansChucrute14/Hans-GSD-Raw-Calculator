"""Backward compatibility wrapper for gsd.core"""
from gsd import core as _core

__all__ = _core.__all__
globals().update({k: getattr(_core, k) for k in _core.__all__})