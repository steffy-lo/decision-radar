"""Validate model candidates against an ingested source before publication."""

from dataclasses import dataclass
from calendar import month_abbr, month_name
from hashlib import sha256
import re
from typing import Literal, Protocol
from decimal import Decimal
from datetime import date

from pydantic import Field, TypeAdapter, ValidationError, model_validator

from services.radar.domain.models import DateValue, DecimalValue, EnumValue, EvidenceRef, Fact, Id, RadarModel, Source, TypedValue
from services.radar.services.source_versions import normalize_text, resolve_quote


class ExtractionError(ValueError):
    """A model response cannot be safely used as project evidence."""


class RawNonDecimalValue(RadarModel):
    @model_validator(mode="before")
    @classmethod
    def omit_legacy_null_unit(cls, value):
        # Older candidates included unit:null for every type. Do not expose a
        # null-only field in the Vertex schema; Vertex requires a concrete type.
        if isinstance(value, dict) and value.get("unit", object()) is None:
            return {key: item for key, item in value.items() if key != "unit"}
        return value


class RawDateValue(RawNonDecimalValue):
    type: Literal["date"]
    value: date = Field(description="A complete calendar date in YYYY-MM-DD format. Never infer a missing year.")


class RawDecimalValue(RadarModel):
    type: Literal["decimal"]
    value: Decimal = Field(allow_inf_nan=False, description="The numeric amount only, without currency symbols or units.")
    unit: str = Field(min_length=1, description="The explicit unit from the source, for example USD or days.")


class RawEnumValue(RawNonDecimalValue):
    type: Literal["enum"]
    value: str = Field(min_length=1, description="A nonempty status or category supported by the quote.")


# An ordinary union produces anyOf, supported by Vertex structured output.
# Each variant carries the same value constraints as the published domain type.
RawValue = RawDateValue | RawDecimalValue | RawEnumValue


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
    entity: str = Field(description="The named subject. Use a supplied entity label exactly when the quote identifies it.")
    predicate: str = Field(description="The attribute. Use a supplied predicate label exactly when the quote supports it.")
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
    def generate(
        self, source: Source, *, entity_aliases: tuple[str, ...] = (), predicate_aliases: tuple[str, ...] = (),
    ) -> ExtractionDraft | dict: ...


def extraction_validation_message(error: ValidationError) -> str:
    """Describe failed fields without exposing model output or source content."""
    paths = []
    variants = {"RawDateValue", "RawDecimalValue", "RawEnumValue"}
    issues = error.errors(include_input=False, include_url=False)
    mismatched = {
        issue["loc"][:-1] for issue in issues
        if issue["type"] == "literal_error" and len(issue["loc"]) >= 2
        and issue["loc"][-2] in variants and issue["loc"][-1] == "type"
    }
    for issue in issues:
        if any(issue["loc"][:len(prefix)] == prefix for prefix in mismatched):
            continue
        if issue["type"] == "extra_forbidden":
            continue
        path = ""
        for part in issue["loc"]:
            if part in variants:
                continue
            path += f"[{part}]" if isinstance(part, int) else ("." if path else "") + str(part)
        if path and path not in paths:
            paths.append(path)
    location = f" at {', '.join(paths[:3])}" if paths else ""
    return (
        f"Gemini returned an invalid extraction value{location}. "
        "Dates need YYYY-MM-DD; amounts need a number and unit; text values cannot be blank. "
        "Please retry extraction. No new facts were saved."
    )


class EvidenceValidator:
    """Resolve an exact, unambiguous quote to one immutable snapshot span."""

    def verify(self, source: Source, quote: str, native_url: str) -> VerifiedEvidence:
        if not native_url.startswith("https://"):
            raise ExtractionError("source has no secure native link")
        if not quote or not quote.strip():
            raise ExtractionError("candidate has no evidence quote")
        try:
            span = resolve_quote(source.id, source.content_snapshot, quote,
                                 document=source.mime_type == "application/vnd.google-apps.document")
        except ValueError as exc:
            if str(exc) != "evidence quote is absent from the source snapshot":
                raise ExtractionError(str(exc)) from exc
            # Gemini sometimes replaces document line breaks with spaces. Only
            # accept an otherwise identical quote at one source location, and
            # store the actual source characters in the citation.
            words = re.split(r"\s+", quote.strip())
            pattern = r"\s+".join(re.escape(word) for word in words)
            matches = list(re.finditer(pattern, normalize_text(source.content_snapshot)))
            if len(matches) != 1:
                raise ExtractionError(str(exc)) from exc
            span = resolve_quote(source.id, source.content_snapshot, matches[0].group(),
                                 document=source.mime_type == "application/vnd.google-apps.document")
        if source.version_id and source.version_id != span.version_id:
            raise ExtractionError("source version does not match the text being extracted")
        return VerifiedEvidence(
            ref=EvidenceRef(
                source_id=source.id, source_title=source.name, native_url=native_url,
                quote=span.quote, locator=span.locator,
                source_version_id=span.version_id, span_id=span.id,
            ),
            span_id=span.id, start_offset=span.start, end_offset=span.end,
        )


_TENTATIVE = re.compile(r"\b(?:may|might|could|tentative|possible|unconfirmed|proposed)\b", re.I)
_NEGATED = re.compile(r"\b(?:not|never|no longer|didn't|wasn't)\b", re.I)
_VALUE = TypeAdapter(TypedValue)


def _typed_value(raw: RawValue) -> TypedValue:
    value = {"type": raw.type, "value": raw.value}
    if raw.type == "decimal":
        value["unit"] = raw.unit
    try:
        return _VALUE.validate_python(value)
    except ValidationError as error:
        raise ExtractionError(extraction_validation_message(error)) from error


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
    # Accept the combined wording only when it appears in the quote and has
    # one trusted entity/predicate interpretation.
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
        number = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
        unit = re.escape(value.unit)
        patterns = (
            rf"(?<![\w.-]){unit}\s+({number})(?!\w)",
            rf"(?<![\w.-])({number})\s+{unit}(?!\w)",
        )
        return any(
            Decimal(match.group(1).replace(",", "")) == value.value
            for pattern in patterns for match in re.finditer(pattern, quote, re.I)
        )
    if isinstance(value, EnumValue):
        words = re.split(r"[\s_-]+", value.value.strip())
        phrase = r"[\s_-]+".join(re.escape(word) for word in words)
        return re.search(rf"(?<!\w){phrase}(?!\w)", quote, re.I) is not None
    return False


def _source_context(snapshot: str, start: int, end: int) -> str:
    """Keep qualifiers in the sentence even when Gemini quotes only a fragment."""
    left = max((snapshot.rfind(mark, 0, start) for mark in ".!?\n"), default=-1) + 1
    right = min((position for mark in ".!?\n" if (position := snapshot.find(mark, end - 1)) >= 0), default=len(snapshot))
    return snapshot[left:right]


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
            draft = ExtractionDraft.model_validate(self.generator.generate(
                source, entity_aliases=tuple(known_entities),
                predicate_aliases=tuple(known_predicates or ()),
            ))
        except ValidationError as error:
            raise ExtractionError(extraction_validation_message(error)) from error

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
            elif candidate.modality != "negated" and not _value_visible(value, candidate.quote):
                uncertain = "typed value is not visible in evidence quote"
            elif candidate.modality == "tentative" or _TENTATIVE.search(_source_context(
                source.content_snapshot, evidence.start_offset, evidence.end_offset,
            )):
                uncertain = "source wording is tentative"
            elif candidate.modality == "confirmed" and _NEGATED.search(_source_context(
                source.content_snapshot, evidence.start_offset, evidence.end_offset,
            )):
                uncertain = "source wording may be negated"
            state = "uncertain" if uncertain else "negated" if candidate.modality == "negated" else "ready"
            fact = None
            if entity_id is not None and predicate_id is not None:
                fact_hash = sha256(f"{evidence.span_id}:{entity_id}:{predicate_id}:{value}".encode()).hexdigest()[:20]
                fact = Fact(
                    id=f"fact_{fact_hash}", project_id=source.project_id, source_id=source.id,
                    entity_id=entity_id, predicate=predicate_id, value=value,
                    modality=candidate.modality, evidence=evidence.ref,
                )
            facts.append(ExtractedFact(candidate, value, evidence, entity_id, state, uncertain, fact))
        return ExtractionResult(tuple(decisions), tuple(facts))
