from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt_sha256", "pbkdf2_sha256", "pbkdf2_sha1"],
    default="argon2",
    deprecated="auto",
)


class Hasher:
    MIN_LENGTH = 4

    @staticmethod
    def verify_password(plain_password, hashed_password):
        """
        Verifies the password using any supported algorithm.
        If the hash is outdated, it can be rehashed automatically.
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        """
        Generates a secure hash using the default algorithm.
        """
        if len(password) < Hasher.MIN_LENGTH:
            raise ValueError("Password must be at least 4 characters long.")
        return pwd_context.hash(password)

    @staticmethod
    def hash_password(password):
        return Hasher.get_password_hash(password)

    @staticmethod
    def needs_update(hashed_password):
        """
        Returns True if the stored password hash should be updated (e.g., algorithm deprecated).
        """
        return pwd_context.needs_update(hashed_password)
