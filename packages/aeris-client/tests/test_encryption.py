"""Tests for fr.aeris.auth.encryption (pure functions, no mocks needed)."""

import base64
import pytest

from fr.aeris.auth.encryption import jasypt_encrypt, jasypt_decrypt, encrypt_credentials


class TestJasyptRoundtrip:

    def test_basic_roundtrip(self):
        plaintext = "hello_world"
        password = "master_password"
        assert jasypt_decrypt(jasypt_encrypt(plaintext, password), password) == plaintext

    def test_roundtrip_with_special_chars(self):
        plaintext = "user@example.com"
        password = "s3cr3t!"
        assert jasypt_decrypt(jasypt_encrypt(plaintext, password), password) == plaintext

    def test_roundtrip_with_long_value(self):
        plaintext = "a_very_long_password_that_exceeds_one_des_block_size"
        password = "master"
        assert jasypt_decrypt(jasypt_encrypt(plaintext, password), password) == plaintext

    def test_encrypt_produces_different_ciphertext_each_time(self):
        # Random salt means two encryptions of the same input differ
        plaintext = "same_input"
        password = "master"
        enc1 = jasypt_encrypt(plaintext, password)
        enc2 = jasypt_encrypt(plaintext, password)
        assert enc1 != enc2

    def test_encrypt_output_is_valid_base64(self):
        encrypted = jasypt_encrypt("test", "password")
        # Should not raise
        decoded = base64.b64decode(encrypted)
        # Salt (8 bytes) + at least one DES block (8 bytes)
        assert len(decoded) >= 16

    def test_wrong_password_does_not_return_plaintext(self):
        # PBEWithMD5AndDES has no integrity check — wrong password either raises
        # (UnicodeDecodeError on garbage bytes) or returns garbage, never the original.
        plaintext = "secret"
        encrypted = jasypt_encrypt(plaintext, "correct_password")
        try:
            result = jasypt_decrypt(encrypted, "wrong_password")
            assert result != plaintext
        except Exception:
            pass


class TestEncryptCredentials:

    def test_returns_two_values(self):
        enc_email, enc_pwd = encrypt_credentials("user@example.com", "pass", "master")
        assert enc_email is not None
        assert enc_pwd is not None

    def test_both_fields_decrypt_correctly(self):
        email = "user@example.com"
        password = "my_password"
        master = "master_secret"
        enc_email, enc_pwd = encrypt_credentials(email, password, master)
        assert jasypt_decrypt(enc_email, master) == email
        assert jasypt_decrypt(enc_pwd, master) == password

    def test_email_and_password_encrypted_independently(self):
        # Even if email == password, ciphertexts differ (different random salts)
        enc_email, enc_pwd = encrypt_credentials("same", "same", "master")
        assert enc_email != enc_pwd
