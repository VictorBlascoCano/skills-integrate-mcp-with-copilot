import argparse
import getpass
import hashlib
import json
import secrets
from pathlib import Path


TEACHER_FILE = Path(__file__).with_name("teachers.json")
PASSWORD_ITERATIONS = 310_000


def main():
    parser = argparse.ArgumentParser(description="Add a teacher login account")
    parser.add_argument("username")
    args = parser.parse_args()

    username = args.username.strip()
    if not username:
        parser.error("username cannot be empty")

    password = getpass.getpass("Teacher password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password or password != confirmation:
        parser.error("passwords must be non-empty and match")

    try:
        with TEACHER_FILE.open(encoding="utf-8") as teacher_file:
            data = json.load(teacher_file)
    except FileNotFoundError:
        data = {"teachers": []}
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"cannot read {TEACHER_FILE}: {exc}")

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        parser.error(f"{TEACHER_FILE} must contain a teachers list")
    if any(
        isinstance(account, dict) and account.get("username") == username
        for account in data["teachers"]
    ):
        parser.error(f"teacher account already exists: {username}")

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    data["teachers"].append(
        {
            "username": username,
            "salt": salt.hex(),
            "password_hash": password_hash.hex(),
            "iterations": PASSWORD_ITERATIONS,
        }
    )
    with TEACHER_FILE.open("w", encoding="utf-8") as teacher_file:
        json.dump(data, teacher_file, indent=2)
        teacher_file.write("\n")
    print(f"Added teacher account: {username}")


if __name__ == "__main__":
    main()