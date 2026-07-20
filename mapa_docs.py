"""Backward compatibility wrapper for gsd.mapa"""
from gsd import mapa as _mapa

__all__ = _mapa.__all__
globals().update({k: getattr(_mapa, k) for k in _mapa.__all__})