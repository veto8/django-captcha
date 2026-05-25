import datetime
import hashlib
import json
import logging
import os
import random
import time
from pathlib import Path

from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.encoding import smart_str

from captcha.conf import settings as captcha_settings

logger = logging.getLogger(__name__)

# Heavily based on session key generation in Django
if hasattr(random, "SystemRandom"):
    randrange = random.SystemRandom().randrange
else:
    randrange = random.randrange
MAX_RANDOM_KEY = 18446744073709551616  # 2 << 63

CAPTCHA_STORAGE_PATH = "captcha_store"


class FileSystemCaptchaStore:
    """File-based storage for captcha challenges instead of database."""

    @staticmethod
    def _get_storage_path():
        """Get the base storage path for captcha files."""
        return CAPTCHA_STORAGE_PATH

    @staticmethod
    def _generate_hashkey(challenge, response):
        """Generate a unique hashkey for the captcha."""
        key_ = (
            smart_str(randrange(0, MAX_RANDOM_KEY))
            + smart_str(time.time())
            + smart_str(challenge, errors="ignore")
            + smart_str(response, errors="ignore")
        ).encode("utf8")
        return hashlib.sha1(key_).hexdigest()

    @staticmethod
    def _get_file_path(hashkey):
        """Get the file path for a captcha hashkey."""
        return os.path.join(CAPTCHA_STORAGE_PATH, f"{hashkey}.json")

    @classmethod
    def create(cls, challenge, response):
        """Create and store a new captcha."""
        response = response.lower()
        hashkey = cls._generate_hashkey(challenge, response)
        
        expiration = timezone.now() + datetime.timedelta(
            minutes=int(captcha_settings.CAPTCHA_TIMEOUT)
        )

        data = {
            "challenge": challenge,
            "response": response,
            "hashkey": hashkey,
            "expiration": expiration.isoformat(),
        }

        file_path = cls._get_file_path(hashkey)
        file_content = json.dumps(data)

        default_storage.save(file_path, file_content.encode())
        return hashkey

    @classmethod
    def get(cls, hashkey):
        """Retrieve a captcha by hashkey."""
        file_path = cls._get_file_path(hashkey)

        try:
            content = default_storage.open(file_path, "r").read()
            data = json.loads(content)
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    @classmethod
    def exists(cls, hashkey):
        """Check if a captcha exists."""
        file_path = cls._get_file_path(hashkey)
        return default_storage.exists(file_path)

    @classmethod
    def delete(cls, hashkey):
        """Delete a captcha."""
        file_path = cls._get_file_path(hashkey)
        if default_storage.exists(file_path):
            default_storage.delete(file_path)

    @classmethod
    def remove_expired(cls):
        """Remove all expired captchas."""
        try:
            storage_path = cls._get_storage_path()
            _, file_names = default_storage.listdir(storage_path)
            
            now = timezone.now()
            for file_name in file_names:
                if file_name.endswith(".json"):
                    file_path = os.path.join(storage_path, file_name)
                    try:
                        content = default_storage.open(file_path, "r").read()
                        data = json.loads(content)
                        expiration = timezone.datetime.fromisoformat(data["expiration"])
                        
                        if expiration <= now:
                            default_storage.delete(file_path)
                    except (json.JSONDecodeError, KeyError):
                        # Delete corrupted files
                        default_storage.delete(file_path)
        except FileNotFoundError:
            pass

    @classmethod
    def generate_key(cls, generator=None):
        """Generate a new captcha key."""
        challenge, response = captcha_settings.get_challenge(generator)()
        hashkey = cls.create(challenge, response)
        return hashkey

    @classmethod
    def pick(cls):
        """Pick a random captcha from the pool or generate a new one."""
        if not captcha_settings.CAPTCHA_GET_FROM_POOL:
            return cls.generate_key()

        try:
            storage_path = cls._get_storage_path()
            _, file_names = default_storage.listdir(storage_path)
            
            valid_captchas = []
            now = timezone.now()
            pool_timeout = datetime.timedelta(
                minutes=int(captcha_settings.CAPTCHA_GET_FROM_POOL_TIMEOUT)
            )
            minimum_expiration = now + pool_timeout

            for file_name in file_names:
                if file_name.endswith(".json"):
                    file_path = os.path.join(storage_path, file_name)
                    try:
                        content = default_storage.open(file_path, "r").read()
                        data = json.loads(content)
                        expiration = timezone.datetime.fromisoformat(data["expiration"])
                        
                        if expiration > minimum_expiration:
                            valid_captchas.append(data["hashkey"])
                    except (json.JSONDecodeError, KeyError):
                        pass

            if valid_captchas:
                return random.choice(valid_captchas)
        except FileNotFoundError:
            pass

        logger.error("Couldn't get a captcha from pool, generating")
        return cls.generate_key()

    @classmethod
    def create_pool(cls, count=1000):
        """Pre-generate a pool of captchas."""
        assert count > 0
        while count > 0:
            cls.generate_key()
            count -= 1
