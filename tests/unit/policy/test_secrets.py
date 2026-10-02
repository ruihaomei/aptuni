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
    ("- **Password**: Zq1999abc!", "credential_field"),
    ("- **密码**：Zq19990717", "credential_field"),
    ("`api_key`: q8W2x9zP77Lm", "credential_field"),
    ('{"user": "a", "password": "Zq19990717abc"}', "credential_field"),
    ("creds = {'password': 'Zq1999abc!'}", "credential_field"),
    ("DB_PASSWORD=Zq19990717", "credential_field"),
    ("export GITHUB_TOKEN=Zq19990717abcXYZ", "credential_field"),
    ("| 邮箱 | 密码 |\n| a@b.c | Zq19990717 |", "credential_field"),
    ("| password | Zq1999abc! |", "credential_field"),
    ("password = \"Zq19990717abc\"", "credential_field"),
    ("- **Password:** Zq1999abc!", "credential_field"),
    ("**密码：** Zq19990717", "credential_field"),
    ("| Site | User | Password | |---|---|---| | mail | a@b.c | Zq1999abc! |", "credential_field"),
    ("client_secret: Zq1999ab", "credential_field"),
    ("access_token=Zq19ab77", "credential_field"),
    ("| Site | Password | |---|---| | mail | Zq1999abc! | ## Budget | Item | Cost | |---|---| | a | b |",
     "credential_field"),
    ("AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzAbCdKEY0", "credential_field"),
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
    "Password: Required",
    "API Key: Required",
    "Access token: Expired",
    "pwd = os.getcwd()",
    "PWD=/Users/someone/code",
    "pwd: ~/code",
    "password = os.getenv('DB_PW')",
    "api_key = os.environ.get('SERVICE_KEY')",
    "access_token = response.json()['access_token']",
    "password = bcrypt.hashpw(pw, salt)",
    "密码 = hashlib.sha256(raw)",
    "pwd: 2024-10-01 notes",
    "passcode: 6-digit",
    "api key: per-user, rotated monthly",
    "password: not-set",
    "**Password**: <your password>",
    '{"password": "********"}',
    "GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }}",
    "| password | string | required |",
    "| token | 512 |",
    "max_tokens: 4096",
    "tokenizer: BertTokenizerFast",
    "token: the smallest unit a tokenizer emits",
    "secret: SecretStr",
    "Secret sauce: patience",
    "the token = word piece mapping in BERT",
    "client_secret: ${CLIENT_SECRET}",
    "password_hash: argon2id",
    "PasswordField(required=True)",
    "token: GPT-4o",
    "token: v2.1.0",
    "eos_token = tokenizer.eos_token",
    "secret: x86_64",
    "| Model | Token | Notes | |---|---|---| | bert | 512 | base |",
    "| Account | Password | |---|---| | mail | rotated 2025 |",
    "| Site | Password | |---|---| | mail | in manager | Results | Score | |---|---| | run | F1-0.93x |",
])
def test_ordinary_notes_about_credentials_are_not_flagged(text: str) -> None:
    assert credential_kinds(text) == ()


def test_worst_case_inputs_stay_linear() -> None:
    import time

    wide = "| " + "password | " * 200 + "\n" + ("| " + "Zq1 | " * 200 + "\n") * 50
    for text in ("a." * 30_000, "password:" * 7_000, "a_" * 30_000 + "password", "| " * 30_000, wide):
        start = time.perf_counter()
        credential_kinds(text)
        assert time.perf_counter() - start < 0.5, text[:20]
