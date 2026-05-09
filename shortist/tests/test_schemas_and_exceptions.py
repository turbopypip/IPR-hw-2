from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.links.exceptions import (
    AliasLengthError,
    InvalidURLFormatError,
    LinkExpiredError,
    PermissionDeniedError,
)
from src.links.schemas import LinkCreate, LinkUpdate


def test_link_create_rounds_expiration_to_minutes():
    expire_at = datetime.now(timezone.utc) + timedelta(days=1, seconds=33)

    link = LinkCreate(original_url="https://example.com", expire_at=expire_at)

    assert link.expire_at.second == 0
    assert link.expire_at.microsecond == 0


def test_link_create_rejects_invalid_alias():
    with pytest.raises(ValidationError):
        LinkCreate(
            original_url="https://example.com",
            custom_alias="bad alias",
            expire_at=None,
        )


def test_link_update_rounds_expiration_to_minutes():
    expire_at = datetime.now(timezone.utc) + timedelta(days=1, seconds=45)

    update = LinkUpdate(
        original_url="https://example.com/new",
        expire_at=expire_at,
    )

    assert update.expire_at.second == 0
    assert update.expire_at.microsecond == 0


def test_custom_link_exceptions_have_expected_status_codes():
    assert AliasLengthError("abc").status_code == 400
    assert LinkExpiredError("gone").status_code == 410
    assert PermissionDeniedError("delete links").status_code == 403
    assert InvalidURLFormatError("example").status_code == 400
