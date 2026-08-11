from datetime import datetime

import pytest
from pydantic import ValidationError

from gridpulse_intelligence.models import GridRegionRecord


def test_grid_region_record_parses_eia_record() -> None:
    raw_record = {
        "period": "2026-08-12T07",
        "respondent": "CAL",
        "respondent-name": "California",
        "type": "DF",
        "type-name": "Day-ahead demand forecast",
        "value": "37905",
        "value-units": "megawatthours",
    }

    record = GridRegionRecord.model_validate(raw_record)

    assert record.period == datetime(2026, 8, 12, 7)
    assert record.respondent == "CAL"
    assert record.respondent_name == "California"
    assert record.record_type == "DF"
    assert record.value == 37905.0
    assert record.value_units == "megawatthours"


def test_grid_region_record_rejects_invalid_period() -> None:
    raw_record = {
        "period": "not-a-date",
        "respondent": "CAL",
        "respondent-name": "California",
        "type": "DF",
        "type-name": "Day-ahead demand forecast",
        "value": "37905",
        "value-units": "megawatthours",
    }

    with pytest.raises(ValidationError):
        GridRegionRecord.model_validate(raw_record)


def test_grid_region_record_rejects_invalid_value() -> None:
    raw_record = {
        "period": "2026-08-12T07",
        "respondent": "CAL",
        "respondent-name": "California",
        "type": "DF",
        "type-name": "Day-ahead demand forecast",
        "value": "not-a-number",
        "value-units": "megawatthours",
    }

    with pytest.raises(ValidationError):
        GridRegionRecord.model_validate(raw_record)
