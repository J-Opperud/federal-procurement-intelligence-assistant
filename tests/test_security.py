from app.utils.security import hash_password, verify_password


def test_password_is_stored_as_a_hash():
    password = "Scout-Test-Password-123!"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert hashed_password


def test_correct_password_passes_verification():
    password = "Scout-Test-Password-123!"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True


def test_incorrect_password_fails_verification():
    hashed_password = hash_password("Scout-Test-Password-123!")

    assert verify_password("Wrong-Password-456!", hashed_password) is False