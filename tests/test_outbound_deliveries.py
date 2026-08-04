"""Tests for outbound WhatsApp delivery persistence."""

from pathlib import Path
from uuid import uuid4

import pytest

import app.outbound_deliveries as storage_module
from app.outbound_deliveries import (
    DELIVERY_STATUS_PENDING,
    DELIVERY_STATUS_RETRY_PENDING,
    DELIVERY_STATUS_SENT,
    OUTBOUND_PROVIDER,
    OutboundDeliveryStorageError,
    create_outbound_delivery,
    delete_outbound_delivery,
    get_outbound_delivery,
    initialize_outbound_deliveries_table,
    list_retry_pending_deliveries,
    mark_outbound_delivery_failed,
    mark_outbound_delivery_sent,
)

TEST_STORAGE_DIRECTORY = Path(".test_storage")


@pytest.fixture
def isolated_outbound_database(
    monkeypatch,
) -> Path:
    """Use a unique project-local SQLite database for each test."""
    TEST_STORAGE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    database_path = (
        TEST_STORAGE_DIRECTORY
        / f"outbound-deliveries-{uuid4().hex}.db"
    )

    monkeypatch.setattr(
        storage_module,
        "get_outbound_delivery_database_path",
        lambda: database_path,
    )

    initialize_outbound_deliveries_table()

    yield database_path

    # Do not delete the database here.
    # Windows may keep a short-lived SQLite file handle open.
    # The complete .test_storage folder is already excluded by Git.


def test_initialize_creates_database(
    isolated_outbound_database: Path,
) -> None:
    """Initialization should create the SQLite database."""
    assert isolated_outbound_database.exists()


def test_create_pending_delivery(
    isolated_outbound_database: Path,
) -> None:
    """A new delivery should start in pending state."""
    delivery_id = create_outbound_delivery(
        inbound_message_id="wamid.inbound-001",
        recipient_phone="2348012345678",
        message="The clinic opens at 8 a.m.",
    )

    assert delivery_id > 0

    record = get_outbound_delivery(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.inbound-001",
    )

    assert record is not None
    assert record["status"] == DELIVERY_STATUS_PENDING
    assert record["attempt_count"] == 0
    assert record["delivery_provider"] is None
    assert record["outbound_message_id"] is None
    assert record["error"] is None


def test_duplicate_delivery_is_rejected(
    isolated_outbound_database: Path,
) -> None:
    """The same inbound message should not create two records."""
    create_outbound_delivery(
        inbound_message_id="wamid.duplicate-001",
        recipient_phone="2348012345678",
        message="First message",
    )

    with pytest.raises(
        OutboundDeliveryStorageError,
        match="already exists",
    ):
        create_outbound_delivery(
            inbound_message_id="wamid.duplicate-001",
            recipient_phone="2348012345678",
            message="Second message",
        )


def test_mark_delivery_sent(
    isolated_outbound_database: Path,
) -> None:
    """A successful attempt should store provider metadata."""
    create_outbound_delivery(
        inbound_message_id="wamid.sent-001",
        recipient_phone="2348012345678",
        message="Your appointment is confirmed.",
    )

    updated = mark_outbound_delivery_sent(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.sent-001",
        delivery_provider="MockWhatsAppSender",
        outbound_message_id="mock-wamid-out-000001",
    )

    assert updated is True

    record = get_outbound_delivery(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.sent-001",
    )

    assert record is not None
    assert record["status"] == DELIVERY_STATUS_SENT
    assert record["attempt_count"] == 1
    assert record["delivery_provider"] == (
        "MockWhatsAppSender"
    )
    assert record["outbound_message_id"] == (
        "mock-wamid-out-000001"
    )
    assert record["error"] is None
    assert record["sent_at"] is not None


def test_mark_delivery_failed(
    isolated_outbound_database: Path,
) -> None:
    """A failed attempt should enter retry-pending state."""
    create_outbound_delivery(
        inbound_message_id="wamid.failed-001",
        recipient_phone="2348012345678",
        message="Your appointment is confirmed.",
    )

    updated = mark_outbound_delivery_failed(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.failed-001",
        error_message="Temporary delivery failure.",
    )

    assert updated is True

    record = get_outbound_delivery(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.failed-001",
    )

    assert record is not None
    assert record["status"] == (
        DELIVERY_STATUS_RETRY_PENDING
    )
    assert record["attempt_count"] == 1
    assert record["error"] == (
        "Temporary delivery failure."
    )


def test_list_retry_pending_deliveries(
    isolated_outbound_database: Path,
) -> None:
    """Only retry-pending records should be listed."""
    create_outbound_delivery(
        inbound_message_id="wamid.retry-001",
        recipient_phone="2348011111111",
        message="Retry message",
    )

    create_outbound_delivery(
        inbound_message_id="wamid.sent-002",
        recipient_phone="2348022222222",
        message="Sent message",
    )

    mark_outbound_delivery_failed(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.retry-001",
        error_message="Temporary failure.",
    )

    mark_outbound_delivery_sent(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.sent-002",
        delivery_provider="MockWhatsAppSender",
        outbound_message_id="mock-out-002",
    )

    records = list_retry_pending_deliveries()

    assert len(records) == 1
    assert records[0]["inbound_message_id"] == (
        "wamid.retry-001"
    )


def test_retry_limit_validation(
    isolated_outbound_database: Path,
) -> None:
    """Retry listing should reject unsafe limits."""
    with pytest.raises(
        ValueError,
        match="at least 1",
    ):
        list_retry_pending_deliveries(
            limit=0
        )

    with pytest.raises(
        ValueError,
        match="cannot exceed",
    ):
        list_retry_pending_deliveries(
            limit=101
        )


def test_missing_delivery_returns_none(
    isolated_outbound_database: Path,
) -> None:
    """Unknown delivery IDs should return no record."""
    assert get_outbound_delivery(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.missing",
    ) is None


def test_mark_missing_delivery_returns_false(
    isolated_outbound_database: Path,
) -> None:
    """Updating a missing record should report false."""
    assert mark_outbound_delivery_sent(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.missing",
        delivery_provider="MockWhatsAppSender",
        outbound_message_id="mock-out-missing",
    ) is False

    assert mark_outbound_delivery_failed(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.missing",
        error_message="Missing record.",
    ) is False


def test_delete_delivery(
    isolated_outbound_database: Path,
) -> None:
    """A stored delivery should be removable."""
    create_outbound_delivery(
        inbound_message_id="wamid.delete-001",
        recipient_phone="2348012345678",
        message="Delete me",
    )

    deleted = delete_outbound_delivery(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.delete-001",
    )

    assert deleted is True

    assert get_outbound_delivery(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.delete-001",
    ) is None


def test_delete_missing_delivery_returns_false(
    isolated_outbound_database: Path,
) -> None:
    """Deleting a missing record should report false."""
    assert delete_outbound_delivery(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.missing",
    ) is False