"""Deterministic comparison of confirmed facts against monitored assumptions."""

from dataclasses import dataclass
from typing import Literal

from services.radar.domain.models import Assumption, DateValue, DecimalValue, EnumValue, Fact


@dataclass(frozen=True)
class Comparison:
    classification: Literal["contradicts", "supports", "uncertain"]
    reason_code: str
    delta_days: int | None = None


class Comparator:
    """Classify typed values without asking a model to decide whether they conflict."""

    @staticmethod
    def compare(assumption: Assumption, fact: Fact, *, entity_id: str | None) -> Comparison:
        if entity_id is None or entity_id != fact.entity_id or assumption.predicate != fact.predicate:
            return Comparison("uncertain", "UNLINKED_EVIDENCE")
        if fact.modality != "confirmed":
            return Comparison("uncertain", "UNCONFIRMED_EVIDENCE")

        expected, actual = assumption.expected_value, fact.value
        if isinstance(expected, DateValue) and isinstance(actual, DateValue):
            if assumption.operator != "on_or_before":
                return Comparison("uncertain", "UNSUPPORTED_RULE")
            delta = (actual.value - expected.value).days
            return (Comparison("contradicts", "DATE_AFTER_REQUIRED_BY", delta)
                    if delta > 0 else Comparison("supports", "DATE_ON_OR_BEFORE_REQUIRED_BY"))

        if isinstance(expected, DecimalValue) and isinstance(actual, DecimalValue):
            if assumption.operator != "at_most" or expected.unit.casefold() != actual.unit.casefold():
                return Comparison("uncertain", "INCOMPATIBLE_NUMERIC_VALUE")
            return (Comparison("contradicts", "DECIMAL_ABOVE_MAXIMUM")
                    if actual.value > expected.value else Comparison("supports", "DECIMAL_WITHIN_MAXIMUM"))

        if isinstance(expected, EnumValue) and isinstance(actual, EnumValue):
            if assumption.operator != "equals":
                return Comparison("uncertain", "UNSUPPORTED_RULE")
            return (Comparison("supports", "ENUM_MATCHES_EXPECTED")
                    if actual.value.casefold() == expected.value.casefold()
                    else Comparison("contradicts", "ENUM_DIFFERS_FROM_EXPECTED"))

        return Comparison("uncertain", "INCOMPATIBLE_TYPED_VALUE")
