import pytest

from app.security import TokenError, create_test_token, validate_socket_token


def test_validate_socket_token_accepts_valid_token() -> None:
    secret = "test-secret-test-secret-test-secret"
    token = create_test_token("student-1", secret)

    decoded = validate_socket_token(token, secret, "HS256")

    assert decoded["sub"] == "student-1"


@pytest.mark.parametrize("token", [None, "", "invalid.token.value"])
def test_validate_socket_token_rejects_invalid_tokens(token: str | None) -> None:
    with pytest.raises(TokenError):
        validate_socket_token(token, "test-secret", "HS256")
