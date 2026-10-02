from src.core.passwords import hash_password, verify_password


def test_hash_password_does_not_store_plain_password():
    password = "TestPassword123!"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)


def test_same_password_gets_different_hashes():
    password = "TestPassword123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password(
        "CorrectPassword123!"
    )

    assert not verify_password(
        "WrongPassword123!",
        password_hash,
    )