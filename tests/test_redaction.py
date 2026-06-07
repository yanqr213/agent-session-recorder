from agent_session_recorder.redaction import REDACTION_MARK, Redactor


def test_redacts_openai_style_key():
    fake_key = "sk-" + "a" * 24
    redacted = Redactor().redact(f"token {fake_key}")
    assert REDACTION_MARK in redacted
    assert fake_key not in redacted


def test_redacts_assignment_secret():
    secret_name = "password"
    redacted = Redactor().redact(secret_name + "=sample-value")
    assert redacted == secret_name + "=" + REDACTION_MARK


def test_redacts_url_credentials():
    redacted = Redactor().redact("https://user:pass@service.test/path")
    assert redacted == f"https://{REDACTION_MARK}:{REDACTION_MARK}@service.test/path"


def test_custom_redaction_pattern():
    redacted = Redactor(["ticket-[0-9]+"]).redact("ticket-123 should be hidden")
    assert redacted == "[REDACTED] should be hidden"
