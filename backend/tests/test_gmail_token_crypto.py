import pytest
from cryptography.fernet import Fernet

from app.services.gmail_token_crypto import (
    GmailTokenConfigurationError,
    GmailTokenCrypto,
    GmailTokenCryptoError,
    parse_gmail_encryption_keys,
)


def new_key() -> str:
    return Fernet.generate_key().decode("ascii")


def test_encrypt_decrypt_round_trip():
    crypto = GmailTokenCrypto([new_key()])
    token = "fictional-refresh-token"
    ciphertext = crypto.encrypt(token)

    assert isinstance(ciphertext, bytes)
    assert ciphertext != token.encode("utf-8")
    assert token.encode("utf-8") not in ciphertext
    assert crypto.decrypt(ciphertext) == token


def test_same_token_uses_randomized_encryption():
    crypto = GmailTokenCrypto([new_key()])

    assert crypto.encrypt("fictional-token") != crypto.encrypt("fictional-token")


def test_tampered_ciphertext_fails_without_revealing_token():
    crypto = GmailTokenCrypto([new_key()])
    ciphertext = bytearray(crypto.encrypt("fictional-token"))
    ciphertext[-1] ^= 1

    with pytest.raises(GmailTokenCryptoError, match="could not be decrypted") as error:
        crypto.decrypt(bytes(ciphertext))

    assert "fictional-token" not in str(error.value)


def test_key_rotation_decrypts_old_ciphertext_and_reencrypts_with_new_key():
    old_key = new_key()
    new_key_value = new_key()
    old_crypto = GmailTokenCrypto([old_key])
    rotated_crypto = GmailTokenCrypto([new_key_value, old_key])

    rotated = rotated_crypto.rotate(old_crypto.encrypt("fictional-token"))

    assert rotated_crypto.decrypt(rotated) == "fictional-token"
    assert GmailTokenCrypto([new_key_value]).decrypt(rotated) == "fictional-token"


def test_parse_keys_trims_and_ignores_empty_entries():
    first = new_key()
    second = new_key()

    assert parse_gmail_encryption_keys(f" {first},,{second} ") == [first, second]


@pytest.mark.parametrize("raw_keys", [None, "", " , "])
def test_missing_keys_fail_closed(raw_keys):
    with pytest.raises(GmailTokenConfigurationError):
        parse_gmail_encryption_keys(raw_keys)


def test_invalid_key_fails_closed():
    with pytest.raises(GmailTokenConfigurationError):
        GmailTokenCrypto(["not-a-fernet-key"])


def test_factory_requires_configured_keys(monkeypatch):
    from app.core import config
    from app.services.gmail_token_crypto import get_gmail_token_crypto

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: config.Settings(db_password="test", gmail_token_encryption_keys=None),
    )

    with pytest.raises(GmailTokenConfigurationError):
        get_gmail_token_crypto()
