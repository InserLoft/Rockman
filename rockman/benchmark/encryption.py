"""Hidden test encryption using AES-256-GCM"""

import os
import base64
import hashlib
import hmac
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class HiddenTestEncryption:
    """
    Encrypts/decrypts hidden tests using AES-256-GCM.
    Key is derived from benchmark version + task_id + master secret.
    """

    MASTER_SECRET_ENV = "ROCKMAN_MASTER_SECRET"
    KEY_LENGTH = 32
    NONCE_LENGTH = 12
    TAG_LENGTH = 16

    def __init__(self, master_secret: Optional[str] = None, benchmark_version: str = "v0.2"):
        self.benchmark_version = benchmark_version
        self.master_secret = master_secret or os.environ.get(self.MASTER_SECRET_ENV)
        if not self.master_secret:
            raise ValueError(
                f"Master secret required. Set {self.MASTER_SECRET_ENV} env var or pass master_secret parameter."
            )
        self._key_cache: dict[str, bytes] = {}

    def _derive_key(self, task_id: str) -> bytes:
        cache_key = f"{self.benchmark_version}:{task_id}"
        if cache_key in self._key_cache:
            return self._key_cache[cache_key]

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=self.benchmark_version.encode(),
            info=task_id.encode(),
        )
        key = hkdf.derive(self.master_secret.encode())
        self._key_cache[cache_key] = key
        return key

    def encrypt(self, task_id: str, plaintext: str) -> Tuple[str, str, str]:
        """
        Encrypt hidden test content.
        Returns: (encrypted_b64, nonce_b64, tag_b64)
        """
        key = self._derive_key(task_id)
        aesgcm = AESGCM(key)
        nonce = os.urandom(self.NONCE_LENGTH)
        plaintext_bytes = plaintext.encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)
        tag = ciphertext[-self.TAG_LENGTH:]
        encrypted = ciphertext[:-self.TAG_LENGTH]
        return (
            base64.b64encode(encrypted).decode(),
            base64.b64encode(nonce).decode(),
            base64.b64encode(tag).decode(),
        )

    def decrypt(self, task_id: str, encrypted_b64: str, nonce_b64: str, tag_b64: str) -> str:
        """Decrypt hidden test content."""
        key = self._derive_key(task_id)
        aesgcm = AESGCM(key)
        nonce = base64.b64decode(nonce_b64)
        encrypted = base64.b64decode(encrypted_b64)
        tag = base64.b64decode(tag_b64)
        ciphertext = encrypted + tag
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode("utf-8")

    def encrypt_problem_hidden_tests(self, problem: "Problem") -> "Problem":
        """Encrypt hidden tests in a Problem object."""
        if problem.hidden_test_encrypted:
            return problem

        from rockman.benchmark.schema import Problem
        hidden_content = problem.metadata.get("_hidden_test_raw", "")
        if hidden_content:
            enc, nonce, tag = self.encrypt(problem.task_id, hidden_content)
            problem.hidden_test_encrypted = enc
            problem.hidden_test_nonce = nonce
            problem.hidden_test_tag = tag
            problem.metadata.pop("_hidden_test_raw", None)
        return problem

    def decrypt_problem_hidden_tests(self, problem: "Problem") -> str:
        """Decrypt hidden tests from a Problem object."""
        if not problem.hidden_test_encrypted:
            return ""
        return self.decrypt(
            problem.task_id,
            problem.hidden_test_encrypted,
            problem.hidden_test_nonce,
            problem.hidden_test_tag,
        )


def create_encryption_from_env(benchmark_version: str = "v0.2") -> HiddenTestEncryption:
    """Factory to create encryption from environment."""
    return HiddenTestEncryption(benchmark_version=benchmark_version)


def generate_master_secret() -> str:
    """Generate a new master secret for key derivation."""
    return base64.b64encode(os.urandom(32)).decode()


def verify_master_secret(master_secret: str, benchmark_version: str, task_id: str, 
                         encrypted_b64: str, nonce_b64: str, tag_b64: str) -> bool:
    """Verify a master secret can decrypt a test."""
    try:
        enc = HiddenTestEncryption(master_secret, benchmark_version)
        enc.decrypt(task_id, encrypted_b64, nonce_b64, tag_b64)
        return True
    except Exception:
        return False