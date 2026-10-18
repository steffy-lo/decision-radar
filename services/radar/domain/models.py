"""Shared MVP contract. JSON field names are camelCase in Python and TypeScript."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic.alias_generators import to_camel


class RadarModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


Id = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")]
Quote = Annotated[str, StringConstraints(min_length=1)]
NonEmpty = Annotated[str, StringConstraints(min_length=1)]


class ProjectMember(RadarModel):
    uid: str
    role: Literal["admin", "editor", "viewer"]
    refresh_folder_id: str | None = Field(default=None, min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")


class AuthenticatedProjectMember(ProjectMember):
    project_id: str


ConnectionStatus = Literal[
    "pending", "active", "needs_reconnect", "disconnected", "error"
]
GOOGLE_DRIVE_CONNECTION_ID = "google-drive"
GOOGLE_MEET_CONNECTION_ID = "google-meet"


class Connection(BaseModel):
    """Safe metadata for a project Google service grant.

    Refresh tokens live only in Secret Manager and are deliberately absent here.
    """

    id: str = GOOGLE_DRIVE_CONNECTION_ID
    project_id: str
    status: ConnectionStatus
    secret_name: Optional[str] = None
    account_email: Optional[str] = None
    selected_folder_id: Optional[str] = None
    error_code: Optional[str] = None
    connected_by_uid: Optional[str] = None
    authorization_pending: bool = False
    export_scope_granted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConnectionStatusResponse(BaseModel):
    """Connection state safe to return through the browser-facing API."""

    id: str = GOOGLE_DRIVE_CONNECTION_ID
    project_id: str
    status: ConnectionStatus
    account_email: Optional[str] = None
    selected_folder_id: Optional[str] = None
    error_code: Optional[str] = None
    authorization_pending: bool = False
    export_scope_granted: bool = False
    updated_at: Optional[datetime] = None


class OAuthState(BaseModel):
    project_id: str
    initiating_uid: str
    browser_nonce_hash: str
    expires_at: datetime
    connection_id: str = GOOGLE_DRIVE_CONNECTION_ID


class AuthorizeConnectionResponse(BaseModel):
    authorization_url: str


class AccessToken(BaseModel):
    token: str
    expires_in: Optional[int] = None


class EvidenceRef(RadarModel):
    source_id: Id
    source_title: str
    native_url: str
    quote: Quote
    locator: str | None = None
    source_version_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    span_id: str | None = Field(default=None, exclude_if=lambda value: value is None)


class DateValue(RadarModel):
    type: Literal["date"]
    value: date


class DecimalValue(RadarModel):
    type: Literal["decimal"]
    value: Decimal
    unit: NonEmpty


class EnumValue(RadarModel):
    type: Literal["enum"]
    value: NonEmpty


TypedValue = Annotated[Union[DateValue, DecimalValue, EnumValue], Field(discriminator="type")]


class Source(RadarModel):
    id: Id
    project_id: Id
    name: str
    mime_type: str
    content_snapshot: str
    status: Literal["ready", "failed", "access_required"]
    version_id: str | None = Field(default=None, exclude_if=lambda value: value is None)


class Decision(RadarModel):
    id: Id
    project_id: Id
    statement: str
    owner: str
    rationale: str
    status: Literal["draft", "active", "retired"]
    active_revision: int = Field(ge=1)


class DecisionRevision(RadarModel):
    id: Id
    decision_id: Id
    revision: int = Field(ge=1)
    statement: str
    evidence: EvidenceRef


class Assumption(RadarModel):
    id: Id
    decision_id: Id
    decision_revision: int = Field(ge=1)
    statement: str
    predicate: str
    operator: Literal["on_or_before", "at_most", "equals"]
    expected_value: TypedValue
    criticality: Literal["low", "medium", "high"]
    evidence: EvidenceRef
    status: Literal["draft", "active", "retired"]


class Fact(RadarModel):
    id: Id
    project_id: Id
    source_id: Id
    entity_id: Id
    predicate: str
    value: TypedValue
    modality: Literal["confirmed", "tentative", "negated"]
    evidence: EvidenceRef


class Dependency(RadarModel):
    id: Id
    project_id: Id
    from_decision_id: Id
    to_decision_id: Id
    relation_type: Literal["enables", "requires_review_of"]
    impact_description: str


class Finding(RadarModel):
    id: Id
    project_id: Id
    assumption_id: Id
    fact_id: Id
    classification: Literal["contradicts", "supports", "uncertain"]
    reason_code: str
    baseline_value: TypedValue
    extracted_value: TypedValue
    delta_days: int | None
    baseline_evidence: EvidenceRef
    update_evidence: EvidenceRef

    @model_validator(mode="after")
    def valid_date_delta(self) -> "Finding":
        if self.reason_code == "DATE_AFTER_REQUIRED_BY":
            if not isinstance(self.baseline_value, DateValue) or not isinstance(self.extracted_value, DateValue):
                raise ValueError("DATE_AFTER_REQUIRED_BY requires date values")
            expected = (self.extracted_value.value - self.baseline_value.value).days
            if self.classification != "contradicts" or expected <= 0 or self.delta_days != expected:
                raise ValueError("date contradiction requires exact positive calendar-day delta")
        return self


class Alert(RadarModel):
    id: Id
    project_id: Id
    finding_id: Id
    decision_id: Id
    decision_revision: int = Field(ge=1)
    severity: Literal["low", "medium", "high"]
    review_state: Literal["open", "kept", "revised", "retired", "dismissed", "clarification_requested"]
    created_at: datetime


class Review(RadarModel):
    id: Id
    alert_id: Id
    action: Literal["keep", "revise", "retire", "dismiss", "request_clarification"]
    rationale: str
    actor_id: NonEmpty
    decision_revision: int = Field(ge=1)
    before_revision: int | None = None
    after_revision: int | None = None
    created_at: datetime


class Brief(RadarModel):
    id: Id
    project_id: Id
    alert_ids: list[Id]
    content: str
    created_at: datetime


class Export(RadarModel):
    id: Id
    brief_id: Id
    provider: Literal["google_docs"]
    status: Literal["queued", "completed", "failed"]
    native_url: str | None


class DemoFixture(RadarModel):
    project_id: Id
    sources: list[Source]
    decisions: list[Decision]
    revisions: list[DecisionRevision]
    assumptions: list[Assumption]
    facts: list[Fact]
    dependencies: list[Dependency]
    findings: list[Finding]
    alerts: list[Alert]
    reviews: list[Review]
    briefs: list[Brief]
    exports: list[Export]

    @model_validator(mode="after")
    def validate_references_and_evidence(self) -> "DemoFixture":
        collections = {
            "sources": self.sources, "decisions": self.decisions, "revisions": self.revisions,
            "assumptions": self.assumptions, "facts": self.facts, "dependencies": self.dependencies,
            "findings": self.findings, "alerts": self.alerts, "reviews": self.reviews,
            "briefs": self.briefs, "exports": self.exports,
        }
        for name, rows in collections.items():
            if len({row.id for row in rows}) != len(rows):
                raise ValueError(f"duplicate ID in {name}")
        sources = {row.id: row for row in self.sources}
        decisions = {row.id: row for row in self.decisions}
        assumptions = {row.id: row for row in self.assumptions}
        facts = {row.id: row for row in self.facts}
        findings = {row.id: row for row in self.findings}
        alerts = {row.id: row for row in self.alerts}
        briefs = {row.id: row for row in self.briefs}
        for rows in collections.values():
            for row in rows:
                if hasattr(row, "project_id") and row.project_id != self.project_id:
                    raise ValueError("cross-project fixture record")
                for value in row.__dict__.values():
                    if isinstance(value, EvidenceRef):
                        source = sources.get(value.source_id)
                        if source is None or value.quote not in source.content_snapshot:
                            raise ValueError("evidence quote must occur verbatim in its source")
        for row in self.revisions:
            if row.decision_id not in decisions:
                raise ValueError("revision decision missing")
        for row in self.assumptions:
            if row.decision_id not in decisions:
                raise ValueError("assumption decision missing")
        for row in self.facts:
            if row.source_id not in sources or row.evidence.source_id != row.source_id:
                raise ValueError("fact source missing or mismatched")
        for row in self.dependencies:
            if row.from_decision_id not in decisions or row.to_decision_id not in decisions:
                raise ValueError("dependency decision missing")
            if row.from_decision_id == row.to_decision_id:
                raise ValueError("self dependency")
        for row in self.findings:
            if row.assumption_id not in assumptions or row.fact_id not in facts:
                raise ValueError("finding input missing")
        for row in self.alerts:
            if row.finding_id not in findings or row.decision_id not in decisions:
                raise ValueError("alert finding or decision missing")
        for row in self.reviews:
            if row.alert_id not in alerts:
                raise ValueError("review alert missing")
        for row in self.briefs:
            if any(alert_id not in alerts for alert_id in row.alert_ids):
                raise ValueError("brief alert missing")
        for row in self.exports:
            if row.brief_id not in briefs:
                raise ValueError("export brief missing")
        return self
