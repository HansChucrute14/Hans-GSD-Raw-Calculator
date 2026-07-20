"""Backward compatibility wrapper for gsd.nutrition"""
from gsd import nutrition as _nutrition

__all__ = _nutrition.__all__
globals().update({k: getattr(_nutrition, k) for k in _nutrition.__all__})