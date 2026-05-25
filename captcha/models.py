"""
Django-captcha models for file-based storage.

This module provides backward compatibility with the old CaptchaStore model API
by wrapping the new FileSystemCaptchaStore class. It allows existing code to continue
using the familiar CaptchaStore interface while benefiting from file-based storage.

The actual file storage implementation is in captcha.storage.FileSystemCaptchaStore.
"""

import logging

from captcha.storage import FileSystemCaptchaStore

logger = logging.getLogger(__name__)


class CaptchaStore:
    """
    Backward-compatible wrapper for FileSystemCaptchaStore.
    
    This class maintains the same API as the old database model but uses
    file-based storage instead of a database.
    """

    @classmethod
    def generate_key(cls, generator=None):
        """Generate a new captcha key."""
        return FileSystemCaptchaStore.generate_key(generator)

    @classmethod
    def pick(cls):
        """Pick a random captcha from the pool or generate a new one."""
        return FileSystemCaptchaStore.pick()

    @classmethod
    def create_pool(cls, count=1000):
        """Pre-generate a pool of captchas."""
        return FileSystemCaptchaStore.create_pool(count)

    @classmethod
    def remove_expired(cls):
        """Remove all expired captchas."""
        return FileSystemCaptchaStore.remove_expired()
