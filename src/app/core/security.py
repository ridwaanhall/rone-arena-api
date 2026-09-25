from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import SECRET_KEY


class KeyDeriver:
    """Derives stable fernet keys from the configured secret."""

    @staticmethod
    def derive_key(secret_key: str) -> bytes:
        key = hashlib.sha256(secret_key.encode()).digest()
        return base64.urlsafe_b64encode(key)


class CryptoManager:
    """Encrypt/decrypt helper used to decode private upstream route prefixes."""

    def __init__(self, secret_key: str) -> None:
        self.key = KeyDeriver.derive_key(secret_key)
        self.fernet = Fernet(self.key)

    def encrypt(self, text: str) -> bytes:
        return self.fernet.encrypt(text.encode())

    def decrypt(self, token: bytes) -> str:
        return self.fernet.decrypt(token).decode()


class BasePathProvider:
    RONE_DEV_KEY = (
        b"gAAAAABoeVABaPKjWkRGpRV7c7bmRASNq4aZcN_cLGeeWU0OSNFtWLahn4mn9AYq4PqpkJKjA8rx4-Jk2oqjfLTB7l3u9tC_ufGi1x5IcdWrinV26tcdotw="
    )
    RONE_DEV_KEY_ACADEMY = (
        b"gAAAAABpaSKzi3z9M7b34iNDxcorLbqIM4CPoZ9-7a8oRpsPPyOUp9V9_ryz73YtFxetZnSCeN-45aLRCAMCZ0BuSPFaMBi1KOXC8b9IYEoc_7ugqf08F8s="
    )
    RONE_DEV_KEY_RATINGS = (
        b"gAAAAABpai4vioAXeSKebTbTHF4axGxoDSpemtjS9eO7mr-ZSmAQW4L88-GD50EMTT_lOXIMceQC-HsJ_P0f2_22t-d43e6srAl1UxQfuAN3MjeqjB4-Kd0="
    )

    @classmethod
    def get_base_path(cls) -> str:
        return CryptoManager(SECRET_KEY).decrypt(cls.RONE_DEV_KEY)

    @classmethod
    def get_base_path_academy(cls) -> str:
        return CryptoManager(SECRET_KEY).decrypt(cls.RONE_DEV_KEY_ACADEMY)

    @classmethod
    def get_base_path_ratings(cls) -> str:
        return CryptoManager(SECRET_KEY).decrypt(cls.RONE_DEV_KEY_RATINGS)


class BaseUserPathProvider:
    RONE_DEV_KEY_AUTH = (
        b"gAAAAABpv9lxb0XK9Gsa41L-d2gn4qZ2hEM9PXFV83nVXYUddiyUOAsev0SpyJ3uXuwLjlpMmZIO_267f7C1QKQGZWRjy4p0lTMlkNnVKVK1tqZeJ5eCg7W9xkRc7ALT2BqGbg2Y65LG"
    )
    
    RONE_DEV_KEY_DATA = (
        b"gAAAAABpv9n0ZIXgs7cuHKxXhR5-41rdZ2mbaSVT0VKUrfvtr3nkKYSFgIb-MhShVpkgujWBc40ID4jw0NShGVsPCPuqj_9EWg6qy_Idn1I0Uv3D7wlinm3wN7_TeGecSiLcSFoqSdxO"
    )
    
    RONE_DEV_KEY_STATS = (
        b"gAAAAABpv9o31xVMkulczTaQAkXyGYT48lgg5mXwspF5f3eOtHUl_G7KIRvxDzmM46Y5FxSlheJy2Ptty7dniI3-a-vQNJBJMhIxEHMzv92yeFakKzONZAQnq-VTn2wceB_Ic9yJLkRK"
    )

    @classmethod
    def get_base_url_path_auth(cls) -> str:
        return CryptoManager(SECRET_KEY).decrypt(cls.RONE_DEV_KEY_AUTH)

    @classmethod
    def get_base_url_path_data(cls) -> str:
        return CryptoManager(SECRET_KEY).decrypt(cls.RONE_DEV_KEY_DATA)

    @classmethod
    def get_base_url_path_stats(cls) -> str:
        return CryptoManager(SECRET_KEY).decrypt(cls.RONE_DEV_KEY_STATS)