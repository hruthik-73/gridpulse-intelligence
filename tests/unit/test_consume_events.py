"""Tests for the GridPulse Kafka consumer CLI."""

import argparse

import pytest

import gridpulse_intelligence.consume_events as consume_events


def test_topic_list_parses_multiple_topics() -> None:
    """Comma-separated topics should normalize correctly."""

    result = consume_events.topic_list(" topic.one,topic.two , topic.three ")

    assert result == (
        "topic.one",
        "topic.two",
        "topic.three",
    )


def test_empty_topic_list_fails() -> None:
    """An empty topic argument should be rejected."""

    with pytest.raises(
        argparse.ArgumentTypeError,
        match="At least one Kafka topic",
    ):
        consume_events.topic_list(" , , ")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", 1),
        ("10", 10),
    ],
)
def test_positive_integer(
    value: str,
    expected: int,
) -> None:
    """Positive integers should parse."""

    assert consume_events.positive_integer(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "invalid",
    ],
)
def test_invalid_positive_integer_fails(
    value: str,
) -> None:
    """Non-positive message counts should fail."""

    with pytest.raises(
        argparse.ArgumentTypeError,
    ):
        consume_events.positive_integer(value)
