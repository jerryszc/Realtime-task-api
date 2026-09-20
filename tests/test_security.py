from sqlmodel import Session

from app.core.security import create_access_token, decode_token, get_password_hash, verify_password


def test_password_hashing() -> None:
    hashed = get_password_hash("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_token_roundtrip(session: Session) -> None:
    token = create_access_token("42")
    assert decode_token(token, "access") == "42"
    assert decode_token(token, "refresh") is None
