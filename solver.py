"""Backward compatibility wrapper for gsd.solver"""
from gsd import solver as _solver

__all__ = _solver.__all__
globals().update({k: getattr(_solver, k) for k in _solver.__all__})