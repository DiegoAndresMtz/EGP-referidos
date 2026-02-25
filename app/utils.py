import uuid
import string
import random


def generate_referral_code(length: int = 8) -> str:
    """Generate a short unique referral code."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def generate_uuid_short() -> str:
    """Generate a short UUID-based string."""
    return uuid.uuid4().hex[:8]
