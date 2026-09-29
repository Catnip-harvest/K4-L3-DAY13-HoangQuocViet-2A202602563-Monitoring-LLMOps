from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    out = scrub_text("CCCD của tôi là 001099012345")
    assert "001099012345" not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card_as_one_token() -> None:
    for card in ("4111 1111 1111 1111", "4111-0111-1111-1111", "4111011111111111"):
        out = scrub_text(f"card {card} thanks")
        assert out == "card [REDACTED_CREDIT_CARD] thanks"


def test_scrub_passport() -> None:
    out = scrub_text("Passport C1234567 expires soon")
    assert "C1234567" not in out
    assert "REDACTED_PASSPORT_VN" in out


def test_scrub_leaves_normal_text_alone() -> None:
    text = "How do I debug tail latency for req-1a2b3c4d at 2026-09-29T08:00:00Z?"
    assert scrub_text(text) == text


def test_scrub_value_reaches_nested_fields() -> None:
    from app.pii import scrub_value

    out = scrub_value({"detail": ["call 0987654321"], "n": 3, "inner": {"mail": "a@b.co"}})
    assert out == {
        "detail": ["call [REDACTED_PHONE_VN]"],
        "n": 3,
        "inner": {"mail": "[REDACTED_EMAIL]"},
    }
