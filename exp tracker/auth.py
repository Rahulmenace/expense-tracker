"""
Ultimate Expense Tracker - Auth Service
Uses PBKDF2-HMAC-SHA256 with per-user salt.
"""

import hashlib
import hmac
import os

PBKDF2_ITERATIONS = 100_000

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = bytes.fromhex(salt)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), dk.hex()

def verify_password(password, salt_hex, expected_hash_hex):
    _, hash_hex = hash_password(password, salt_hex)
    return hmac.compare_digest(hash_hex, expected_hash_hex)

class AuthError(Exception):
    pass

class AuthService:
    def __init__(self, db):
        self.db = db

    def register(self, username, password, email=""):
        username = (username or "").strip()
        if len(username) < 3:
            raise AuthError("Username must be at least 3 characters.")
        if len(password) < 4:
            raise AuthError("Password must be at least 4 characters.")
        if self.db.get_user_by_username(username):
            raise AuthError("That username is already taken.")

        salt_hex, hash_hex = hash_password(password)
        user_id = self.db.create_user(username, email, salt_hex, hash_hex)
        return self.db.get_user_by_id(user_id)

    def login(self, username, password):
        username = (username or "").strip()
        user = self.db.get_user_by_username(username)
        if not user or not verify_password(password, user["salt"], user["password_hash"]):
            raise AuthError("Invalid username or password.")
        return user
    