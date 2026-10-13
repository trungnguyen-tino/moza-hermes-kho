"""Đặt lịch hẹn (Google Calendar): tools-only Hermes plugin; ``register`` lives in tools.py."""

from .tools import register  # noqa: F401

__all__ = ["register"]
