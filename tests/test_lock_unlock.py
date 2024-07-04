import os
from difflib import unified_diff

import pytest
import argon2
from lockbyte import lock_unlock


@pytest.fixture
def dummy_user():
    user_password = "abcdef"  # simple password
    salt = os.urandom(32)
    hashing_params = {"type": argon2.low_level.Type.ID,
                      "salt_len": 32,
                      "hash_len": 32,
                      "time_cost": 3,
                      "parallelism": 4}
    hash = argon2.PasswordHasher(**hashing_params).hash(password=user_password, salt=salt)
    return (salt, hash)


@pytest.fixture
def fixed_user():
    user_password = "abcdef"  # simple password
    file_path = "tests/temp/test.txt"
    if not os.path.isdir("tests/temp"):
        os.mkdir("tests/temp")
    if os.path.isfile(file_path.split('.')[-2] + "_decrypted" + ".txt"):
        os.remove(file_path.split('.')[-2] + "_decrypted" + ".txt") # remove file if previously generated
    if os.path.isfile(file_path + ".lockbyte"):
        os.remove(file_path + ".lockbyte") # remove file if previously generated
    if os.path.isfile(file_path):
        os.remove(file_path)  # remove file if previously generated
    with open(file_path, "w") as f:
        f.write('')
    user = lock_unlock.LockByteUser(passphrase=user_password)
    return (user, file_path)


def test_when_correct_password_provided(dummy_user):
    hash = dummy_user[1]
    user = lock_unlock.LockByteUser(passphrase="abcdef")
    assert user.validate_and_generate(0, hash) == True # validate password using hash match


def test_when_wrong_password_provided(dummy_user):
    hash = dummy_user[1]
    user = lock_unlock.LockByteUser(passphrase="abcd")  # pick wrong password
    with pytest.raises(argon2.exceptions.VerifyMismatchError):
        user.validate_and_generate(0, hash)  # raise mimatch error


def test_when_hash_corrupted(dummy_user):
    hash = dummy_user[1]
    user = lock_unlock.LockByteUser(passphrase="abcdef") # pick correct password
    hash = hash[32]+'x'+hash[32:] # modify hash
    with pytest.raises(argon2.exceptions.InvalidHashError):
        assert user.validate_and_generate(0, hash) == True # raise invalid hash error

@pytest.mark.parametrize("test_input, expected", [(0,16), (1,15), (2,14), (3,13), (4,12),
                                                  (5,11), (6,10), (7,9), (8,8), (9,7), (10,6), 
                                                  (11,5), (12,4), (13,3), (14,2), (15,1), (16,16)])
def test_all_block_size_paddings(fixed_user, test_input, expected):
    user, file_path = fixed_user
    with open(file_path, "w") as f:
        for i in range(test_input):
            f.write(str(i%10))
    with open(file_path, "rb") as file:
        if user.validate_and_generate(1):
            user.encrypt(file=file, file_path=file_path)
    assert os.path.getsize(file_path + ".lockbyte")-(134+test_input) == expected


def test_decrypted_file_matches_original_file(fixed_user):
    user, file_path = fixed_user
    with open(file_path, "w") as f:
        f.write("This is a test.")
    with open(file_path, "rb") as f:
        if user.validate_and_generate(1):
            user.encrypt(file=f, file_path=file_path)
    with open(file_path + ".lockbyte", "rb") as f:
        user._key = "abcdef"
        decrypted_file_path = user.decrypt(file=f, file_path=file_path + ".lockbyte")
    with open(file_path, "r") as f:
        expected_lines = f.readlines()
    with open(decrypted_file_path, "r") as f:
        actual_lines = f.readlines()
    diff = list(unified_diff(expected_lines, actual_lines))
    assert diff == [], "Unexpected file contents:\n" + "".join(diff)

