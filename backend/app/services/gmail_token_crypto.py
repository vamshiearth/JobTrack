from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class GmailTokenCryptoError(Exception):
    """A Gmail credential could not be decrypted."""


class GmailTokenConfigurationError(Exception):
    """Gmail token encryption keys are missing or invalid."""


def parse_gmail_encryption_keys(raw_keys: str | None) -> list[str]:
    if not raw_keys:
        raise GmailTokenConfigurationError("Gmail encryption keys are not configured")

    keys = [key.strip() for key in raw_keys.split(",") if key.strip()]
    if not keys:
        raise GmailTokenConfigurationError("Gmail encryption keys are not configured")
    return keys


class GmailTokenCrypto:
    def __init__(self, keys: list[str]):
        if not keys:
            raise GmailTokenConfigurationError("Gmail encryption keys are not configured")
        try:
            self._cipher = MultiFernet([Fernet(key.encode("ascii")) for key in keys])
        except (UnicodeEncodeError, ValueError, TypeError) as exc:
            raise GmailTokenConfigurationError(
                "Invalid Gmail encryption key configuration"
            ) from exc

    def encrypt(self, token: str) -> bytes:
        return self._cipher.encrypt(token.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._cipher.decrypt(ciphertext).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, TypeError, ValueError) as exc:
            raise GmailTokenCryptoError("Gmail credential could not be decrypted") from exc

    def rotate(self, ciphertext: bytes) -> bytes:
        return self.encrypt(self.decrypt(ciphertext))


def get_gmail_token_crypto() -> GmailTokenCrypto:
    from app.core.config import get_settings

    settings = get_settings()
    return GmailTokenCrypto(parse_gmail_encryption_keys(settings.gmail_token_encryption_keys))
