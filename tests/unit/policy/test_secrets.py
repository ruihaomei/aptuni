"""ADR-0031: high-precision credential detection (synthetic values only; none are real)."""

import pytest

from aptuni.policy.secrets import credential_kinds

PEM_HEADER = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"  # split so scanners do not flag this test file


@pytest.mark.parametrize(("text", "kind"), [
    ("163 邮箱：someone@example.com；密码：Zq19990717abc", "credential_field"),
    ("学信网：13800000000；密码：Abc12345", "credential_field"),
    ("password: hunter2!x", "credential_field"),
    ("Password=Tr0ub4dor&3 for the lab VM", "credential_field"),
    ("api_key = q8W2-x9zP-77Lm-Qa1b", "credential_field"),
    ("登录密码 = 20050622", "credential_field"),
    ("OPENAI " + "sk-" + "proj-" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4", "provider_token"),
    ("token " + "ghp_" + "A" * 36, "provider_token"),
    ("AWS " + "AKIA" + "ABCDEFGHIJKLMNOP", "provider_token"),
    ("Authorization: " + "Bearer " + "abcDEF123456ghiJKL789012mnoPQR", "provider_token"),
    (PEM_HEADER + "\nb3BlbnNzaC1rZXktdjEAAAAA", "private_key"),
    ("jwt " + "eyJ" + "hbGciOiJIUzI1NiJ9" + ".eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0" + ".dozjgNryP4J3jVmNHl0w5N", "jwt"),
    ("db: postgres://admin:S3cr3tPw@db.internal:5432/app", "url_credentials"),
])
def test_obvious_credentials_are_detected(text: str, kind: str) -> None:
    assert kind in credential_kinds(text)


@pytest.mark.parametrize("text", [
    "密码学基础：对称加密与非对称加密",
    "Use a password manager; a strong password has at least 12 characters.",
    "password: ******",
    "password: <your password>",
    "password: required",
    "API key: stored in an environment variable",
    "密码：见密码本",
    "password: changeme",
    "Password hashing with bcrypt and salting.",
    "postgres://user:password@localhost/db",
    "token: tokenization in NLP pipelines",
    "The secret: practice every day",
    "sk-learn is not a token; scikit-learn pipelines",
    "PIN: 1234 example in the docs",
])
def test_ordinary_notes_about_credentials_are_not_flagged(text: str) -> None:
    assert credential_kinds(text) == ()
