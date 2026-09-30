"""Validate model candidates against an ingested source before publication."""

from dataclasses import dataclass
from calendar import month_abbr, month_name
from hashlib import sha256
import re
from typing import Literal, Protocol
from decimal import Decimal

from pydantic import Field, TypeAdapter, ValidationError

from services.radar.domain.models import DateValue, DecimalValue, EvidenceRef, Fact, Id, RadarModel, Source, TypedValue


class ExtractionError(ValueError):
    """A model response cannot be safely used as project evidence."""


class RawValue(RadarModel):
    type: Literal["date", "decimal", "enum"]
    value: str
    unit: str | None = None


class RawAssumption(RadarModel):
    statement: str
    entity: str
    predicate: str
    operator: Literal["on_or_before", "at_most", "equals"]
    expected_value: RawValue
    criticality: Literal["low", "medium", "high"]
    quote: str


class RawDecision(RadarModel):
    statement: str
    owner: str | None = None
    rationale: str
    quote: str
    assumptions: list[RawAssumption] = Field(default_factory=list)


class RawFact(RadarModel):
    entity: str
    predicate: str
    value: RawValue
    modality: Literal["confirmed", "tentative", "negated"]
    quote: str
    context_complete: bool = False


class ExtractionDraft(RadarModel):
    decisions: list[RawDecision] = Field(default_factory=list)
    facts: list[RawFact] = Field(default_factory=list)


@dataclass(frozen=True)
class VerifiedEvidence:
    ref: EvidenceRef
    span_id: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class ExtractedAssumption:
    candidate: RawAssumption
    expected_value: TypedValue
    evidence: VerifiedEvidence
    entity_id: str | None
    uncertain_reason: str | None


@dataclass(frozen=True)
class ExtractedDecision:
    candidate: RawDecision
    evidence: VerifiedEvidence
    assumptions: tuple[ExtractedAssumption, ...]
    uncertain_reason: str | None


@dataclass(frozen=True)
class ExtractedFact:
    candidate: RawFact
    value: TypedValue
    evidence: VerifiedEvidence
    entity_id: str | None
    state: Literal["ready", "uncertain", "negated"]
    uncertain_reason: str | None
    fact: Fact | None


@dataclass(frozen=True)
class ExtractionResult:
    decisions: tuple[ExtractedDecision, ...]
    facts: tuple[ExtractedFact, ...]

    @property
    def alert_eligible_facts(self) -> tuple[Fact, ...]:
        return tuple(item.fact for item in self.facts if item.state == "ready" and item.fact is not None)


class CandidateGenerator(Protocol):
    def generate(self, source: Source) -> ExtractionDraft | dict: ...


class EvidenceValidator:
    """Resolve an exact, unambiguous quote to one immutable snapshot span."""

    def verify(self, source: Source, quote: str, native_url: str) -> VerifiedEvidence:
        if not native_url.startswith("https://"):
            raise ExtractionError("source has no secure native link")
        if not quote or not quote.strip():
            raise ExtractionError("candidate has no evidence quote")
        start = source.content_snapshot.find(quote)
        if start < 0:
            raise ExtractionError("evidence quote is absent from the source snapshot")
        if source.content_snapshot.find(quote, start + 1) >= 0:
            raise ExtractionError("evidence quote matches more than one source span")
        end = start + len(quote)
        snapshot_hash = sha256(source.content_snapshot.encode("utf-8")).hexdigest()
        span_hash = sha256(f"{source.id}:{snapshot_hash}:{start}:{end}".encode()).hexdigest()[:20]
        return VerifiedEvidence(
            ref=EvidenceRef(source_id=source.id, source_title=source.name, native_url=native_url, quote=quote),
            span_id=f"span_{span_hash}", start_offset=start, end_offset=end,
        )


_TENTATIVE = re.compile(r"\b(?:may|might|could|tentative|possible|unconfirmed|proposed)\b", re.I)
_NEGATED = re.compile(r"\b(?:not|never|no longer|didn't|wasn't)\b", re.I)
_VALUE = TypeAdapter(TypedValue)


def _typed_value(raw: RawValue) -> TypedValue:
    value = {"type": raw.type, "value": raw.value}
    if raw.type == "decimal":
        value["unit"] = raw.unit
    elif raw.unit is not None:
        raise ExtractionError("unit is only valid for decimal values")
    try:
        return _VALUE.validate_python(value)
    except ValidationError as error:
        raise ExtractionError("candidate has an invalid typed value") from error


def _entity_id(name: str, known_entities: dict[str, Id]) -> str | None:
    return {key.strip().casefold(): value for key, value in known_entities.items()}.get(name.strip().casefold())


def _predicate_id(name: str, known_predicates: dict[str, str] | None) -> str | None:
    if known_predicates is None:
        return name
    return {key.strip().casefold(): value for key, value in known_predicates.items()}.get(name.strip().casefold())


def _fact_ids(
    candidate: RawFact, known_entities: dict[str, Id], known_predicates: dict[str, str] | None,
) -> tuple[str | None, str | None]:
    entity_id = _entity_id(candidate.entity, known_entities)
    predicate_id = _predicate_id(candidate.predicate, known_predicates)
    if (entity_id is not None and predicate_id is not None) or known_predicates is None:
        return entity_id, predicate_id

    # Gemini may split one exact source phrase at a different word boundary.
    # Accept the combined wording only when it is in the quote and resolves to
    # one trusted entity/predicate pair. Other paraphrases remain uncertain.
    def normalize(value: str) -> str:
        return " ".join(value.split()).casefold()

    phrase = normalize(f"{candidate.entity} {candidate.predicate}")
    if not re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalize(candidate.quote)):
        return entity_id, predicate_id
    matches = {
        (trusted_entity, trusted_predicate)
        for alias, trusted_entity in known_entities.items()
        for wording, trusted_predicate in known_predicates.items()
        if normalize(f"{alias} {wording}") == phrase
    }
    return next(iter(matches)) if len(matches) == 1 else (entity_id, predicate_id)


def _value_visible(value: TypedValue, quote: str) -> bool:
    if isinstance(value, DateValue):
        day = value.value.day
        year = value.value.year
        month = value.value.month
        forms = (
            value.value.isoformat(),
            f"{month_name[month]} {day}, {year}",
            f"{month_name[month]} {day} {year}",
            f"{month_abbr[month]} {day}, {year}",
            f"{day} {month_name[month]} {year}",
        )
        return any(form.casefold() in quote.casefold() for form in forms)
    if isinstance(value, DecimalValue):
        numbers = re.findall(r"(?<!\w)(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\w)", quote)
        return any(Decimal(number.replace(",", "")) == value.value for number in numbers)
    return True


class Extractor:
    """Validate one source's Gemini candidates before handing facts to KAN-17.

    `known_entities` maps source wording to trusted project entity IDs. A missing
    alias leaves a fact uncertain. `known_predicates` maps model wording to
    monitored predicate IDs; callers publishing facts should supply it so an
    unmapped predicate stays uncertain. `native_url` comes from source metadata,
    not from the model response.
    """

    def __init__(self, generator: CandidateGenerator, validator: EvidenceValidator | None = None):
        self.generator = generator
        self.validator = validator or EvidenceValidator()

    def extract(
        self, source: Source, known_entities: dict[str, Id], native_url: str,
        known_predicates: dict[str, str] | None = None,
    ) -> ExtractionResult:
        if source.status != "ready" or not source.content_snapshot.strip():
            raise ExtractionError("source is not ready for extraction")
        try:
            draft = ExtractionDraft.model_validate(self.generator.generate(source))
        except ValidationError as error:
            raise ExtractionError("model response does not match the extraction schema") from error

        decisions = []
        for candidate in draft.decisions:
            evidence = self.validator.verify(source, candidate.quote, native_url)
            assumptions = []
            for item in candidate.assumptions:
                value = _typed_value(item.expected_value)
                assumption_evidence = self.validator.verify(source, item.quote, native_url)
                entity_id = _entity_id(item.entity, known_entities)
                uncertain_reason = None
                if entity_id is None:
                    uncertain_reason = "assumption entity is unresolved"
                elif not _value_visible(value, item.quote):
                    uncertain_reason = "typed value is not visible in assumption evidence quote"
                assumptions.append(ExtractedAssumption(item, value, assumption_evidence, entity_id, uncertain_reason))
            uncertain = None
            if not candidate.owner or not candidate.owner.strip():
                uncertain = "owner is not identified"
            if any(item.uncertain_reason for item in assumptions):
                uncertain = next(item.uncertain_reason for item in assumptions if item.uncertain_reason)
            decisions.append(ExtractedDecision(candidate, evidence, tuple(assumptions), uncertain))

        facts = []
        for candidate in draft.facts:
            evidence = self.validator.verify(source, candidate.quote, native_url)
            value = _typed_value(candidate.value)
            entity_id, predicate_id = _fact_ids(candidate, known_entities, known_predicates)
            uncertain = None
            if entity_id is None:
                uncertain = "entity is unresolved"
            elif predicate_id is None:
                uncertain = "predicate is unresolved"
            elif not candidate.context_complete:
                uncertain = "source context is incomplete"
            elif not _value_visible(value, candidate.quote):
                uncertain = "typed value is not visible in evidence quote"
            elif candidate.modality == "tentative" or _TENTATIVE.search(candidate.quote):
                uncertain = "source wording is tentative"
            elif candidate.modality == "confirmed" and _NEGATED.search(candidate.quote):
                uncertain = "source wording may be negated"
            state = "uncertain" if uncertain else "negated" if candidate.modality == "negated" else "ready"
            fact = None
            if entity_id is not None and predicate_id is not None:
                fact_hash = sha256(f"{evidence.span_id}:{predicate_id}:{value}".encode()).hexdigest()[:20]
                fact = Fact(
                    id=f"fact_{fact_hash}", project_id=source.project_id, source_id=source.id,
                    entity_id=entity_id, predicate=predicate_id, value=value,
                    modality=candidate.modality, evidence=evidence.ref,
                )
            facts.append(ExtractedFact(candidate, value, evidence, entity_id, state, uncertain, fact))
        return ExtractionResult(tuple(decisions), tuple(facts))
