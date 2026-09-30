/** JSON contract shared with services/radar/domain/models.py. */
export type Id = string;
export type EvidenceRef = { sourceId: Id; sourceTitle: string; nativeUrl: string; quote: string; locator?: string | null };
export type TypedValue =
  | { type: "date"; value: string }
  | { type: "decimal"; value: string | number; unit: string }
  | { type: "enum"; value: string };
export type Source = {
  id: Id; projectId: Id; name: string; mimeType: string; contentSnapshot: string;
  status: "ready" | "failed" | "access_required";
};
export type Decision = {
  id: Id; projectId: Id; statement: string; owner: string; rationale: string;
  status: "draft" | "active" | "retired"; activeRevision: number;
};
export type DecisionRevision = {
  id: Id; decisionId: Id; revision: number; statement: string; evidence: EvidenceRef;
};
export type Assumption = {
  id: Id; decisionId: Id; decisionRevision: number; statement: string; predicate: string;
  operator: "on_or_before" | "at_most" | "equals"; expectedValue: TypedValue;
  criticality: "low" | "medium" | "high"; evidence: EvidenceRef;
  status: "draft" | "active" | "retired";
};
export type Fact = {
  id: Id; projectId: Id; sourceId: Id; entityId: Id; predicate: string;
  value: TypedValue; modality: "confirmed" | "tentative" | "negated"; evidence: EvidenceRef;
};
export type Dependency = {
  id: Id; projectId: Id; fromDecisionId: Id; toDecisionId: Id;
  relationType: "enables" | "requires_review_of"; impactDescription: string;
};
export type Finding = {
  id: Id; projectId: Id; assumptionId: Id; factId: Id;
  classification: "contradicts" | "supports" | "uncertain"; reasonCode: string;
  baselineValue: TypedValue; extractedValue: TypedValue; deltaDays: number | null;
  baselineEvidence: EvidenceRef; updateEvidence: EvidenceRef;
};
export type Alert = {
  id: Id; projectId: Id; findingId: Id; decisionId: Id; decisionRevision: number;
  severity: "low" | "medium" | "high";
  reviewState: "open" | "kept" | "revised" | "retired" | "dismissed";
  createdAt: string;
};
export type Review = {
  id: Id; alertId: Id; action: "keep" | "revise" | "retire" | "dismiss";
  rationale: string; actorId: Id; decisionRevision: number; createdAt: string;
};
export type Brief = {
  id: Id; projectId: Id; alertIds: Id[]; content: string; createdAt: string;
};
export type Export = {
  id: Id; briefId: Id; provider: "google_docs";
  status: "queued" | "completed" | "failed"; nativeUrl: string | null;
};
export type DemoFixture = {
  projectId: Id; sources: Source[]; decisions: Decision[]; revisions: DecisionRevision[];
  assumptions: Assumption[]; facts: Fact[]; dependencies: Dependency[];
  findings: Finding[]; alerts: Alert[]; reviews: Review[]; briefs: Brief[]; exports: Export[];
};

type Check = (value: unknown) => void;
type Shape = Record<string, Check>;
const fail = (message: string): never => { throw new Error(message); };
const object = (value: unknown): Record<string, unknown> => {
  if (typeof value !== "object" || value === null || Array.isArray(value)) fail("expected object");
  return value as Record<string, unknown>;
};
const string: Check = (value) => { if (typeof value !== "string") fail("expected string"); };
const nonempty: Check = (value) => { string(value); if (!(value as string).trim()) fail("empty string"); };
const id: Check = (value) => {
  if (typeof value !== "string" || !/^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/.test(value)) fail("invalid ID");
};
const positiveInt: Check = (value) => {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) fail("expected positive integer");
};
const integer: Check = (value) => {
  if (typeof value !== "number" || !Number.isInteger(value)) fail("expected integer");
};
const choice = (...values: string[]): Check => (value) => {
  if (typeof value !== "string" || !values.includes(value)) fail("invalid enum value");
};
const optional = (check: Check): Check => (value) => {
  if (value !== null && value !== undefined) check(value);
};
const list = (check: Check): Check => (value) => {
  if (!Array.isArray(value)) fail("expected array");
  (value as unknown[]).forEach(check);
};
const shape = (fields: Shape): Check => (value) => {
  const row = object(value);
  for (const [name, check] of Object.entries(fields)) {
    if (!(name in row)) fail(`missing ${name}`);
    check(row[name]);
  }
  for (const name of Object.keys(row)) if (!(name in fields)) fail(`unexpected ${name}`);
};
const isoDate: Check = (value) => {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) fail("invalid date");
  const date = new Date(`${value}T00:00:00Z`);
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== value) fail("invalid calendar date");
};
const timestamp: Check = (value) => {
  if (typeof value !== "string" || !Number.isFinite(Date.parse(value))) fail("invalid timestamp");
};
const decimal: Check = (value) => {
  if ((typeof value !== "string" && typeof value !== "number") ||
      !/^-?(?:0|[1-9]\d*)(?:\.\d+)?$/.test(String(value)) ||
      !Number.isFinite(Number(value))) fail("invalid decimal");
};
const evidence: Check = (value) => {
  const row = object(value);
  for (const name of ["sourceId", "sourceTitle", "nativeUrl", "quote"]) if (!(name in row)) fail(`missing ${name}`);
  id(row.sourceId); nonempty(row.sourceTitle); nonempty(row.nativeUrl); nonempty(row.quote);
  if ("locator" in row) optional(nonempty)(row.locator);
  for (const name of Object.keys(row)) if (!["sourceId", "sourceTitle", "nativeUrl", "quote", "locator"].includes(name)) fail(`unexpected ${name}`);
};
const typedValue: Check = (value) => {
  const kind = object(value).type;
  if (kind === "date") shape({ type: choice("date"), value: isoDate })(value);
  else if (kind === "decimal") shape({ type: choice("decimal"), value: decimal, unit: nonempty })(value);
  else if (kind === "enum") shape({ type: choice("enum"), value: nonempty })(value);
  else fail("invalid typed value");
};
const specs: Record<Exclude<keyof DemoFixture, "projectId">, Check> = {
  sources: shape({ id, projectId: id, name: nonempty, mimeType: nonempty, contentSnapshot: string, status: choice("ready", "failed", "access_required") }),
  decisions: shape({ id, projectId: id, statement: nonempty, owner: nonempty, rationale: string, status: choice("draft", "active", "retired"), activeRevision: positiveInt }),
  revisions: shape({ id, decisionId: id, revision: positiveInt, statement: nonempty, evidence }),
  assumptions: shape({ id, decisionId: id, decisionRevision: positiveInt, statement: nonempty, predicate: nonempty, operator: choice("on_or_before", "at_most", "equals"), expectedValue: typedValue, criticality: choice("low", "medium", "high"), evidence, status: choice("draft", "active", "retired") }),
  facts: shape({ id, projectId: id, sourceId: id, entityId: id, predicate: nonempty, value: typedValue, modality: choice("confirmed", "tentative", "negated"), evidence }),
  dependencies: shape({ id, projectId: id, fromDecisionId: id, toDecisionId: id, relationType: choice("enables", "requires_review_of"), impactDescription: nonempty }),
  findings: shape({ id, projectId: id, assumptionId: id, factId: id, classification: choice("contradicts", "supports", "uncertain"), reasonCode: nonempty, baselineValue: typedValue, extractedValue: typedValue, deltaDays: optional(integer), baselineEvidence: evidence, updateEvidence: evidence }),
  alerts: shape({ id, projectId: id, findingId: id, decisionId: id, decisionRevision: positiveInt, severity: choice("low", "medium", "high"), reviewState: choice("open", "kept", "revised", "retired", "dismissed"), createdAt: timestamp }),
  reviews: shape({ id, alertId: id, action: choice("keep", "revise", "retire", "dismiss"), rationale: nonempty, actorId: id, decisionRevision: positiveInt, createdAt: timestamp }),
  briefs: shape({ id, projectId: id, alertIds: list(id), content: nonempty, createdAt: timestamp }),
  exports: shape({ id, briefId: id, provider: choice("google_docs"), status: choice("queued", "completed", "failed"), nativeUrl: optional(nonempty) }),
};

/** Parse untrusted JSON before the UI consumes it. Also verifies evidence provenance. */
export function parseDemoFixture(value: unknown): DemoFixture {
  const fields: Shape = { projectId: id };
  for (const [name, spec] of Object.entries(specs)) fields[name] = list(spec);
  shape(fields)(value);
  const data = value as DemoFixture;
  const collections = Object.keys(specs) as (keyof typeof specs)[];
  for (const name of collections) {
    const rows = data[name] as { id: string; projectId?: string }[];
    if (new Set(rows.map((row) => row.id)).size !== rows.length) fail(`duplicate ID in ${name}`);
    for (const row of rows) if (row.projectId && row.projectId !== data.projectId) fail("cross-project record");
  }
  const source = new Map(data.sources.map((row) => [row.id, row]));
  const decision = new Set(data.decisions.map((row) => row.id));
  const assumption = new Set(data.assumptions.map((row) => row.id));
  const fact = new Set(data.facts.map((row) => row.id));
  const finding = new Set(data.findings.map((row) => row.id));
  const alert = new Set(data.alerts.map((row) => row.id));
  const brief = new Set(data.briefs.map((row) => row.id));
  const checkEvidence = (ref: EvidenceRef) => {
    const text = source.get(ref.sourceId)?.contentSnapshot;
    if (!text?.includes(ref.quote)) fail("evidence quote absent from source");
  };
  data.revisions.forEach((row) => { if (!decision.has(row.decisionId)) fail("revision decision missing"); checkEvidence(row.evidence); });
  data.assumptions.forEach((row) => { if (!decision.has(row.decisionId)) fail("assumption decision missing"); checkEvidence(row.evidence); });
  data.facts.forEach((row) => { if (!source.has(row.sourceId) || row.evidence.sourceId !== row.sourceId) fail("fact source mismatch"); checkEvidence(row.evidence); });
  data.dependencies.forEach((row) => { if (!decision.has(row.fromDecisionId) || !decision.has(row.toDecisionId) || row.fromDecisionId === row.toDecisionId) fail("invalid dependency"); });
  data.findings.forEach((row) => {
    if (!assumption.has(row.assumptionId) || !fact.has(row.factId)) fail("finding input missing");
    checkEvidence(row.baselineEvidence); checkEvidence(row.updateEvidence);
    if (row.reasonCode === "DATE_AFTER_REQUIRED_BY") {
      if (row.baselineValue.type !== "date" || row.extractedValue.type !== "date") fail("date values required");
      const delta = (
        Date.parse((row.extractedValue as { type: "date"; value: string }).value) -
        Date.parse((row.baselineValue as { type: "date"; value: string }).value)
      ) / 86400000;
      if (row.classification !== "contradicts" || delta <= 0 || row.deltaDays !== delta) fail("invalid date delta");
    }
  });
  data.alerts.forEach((row) => { if (!finding.has(row.findingId) || !decision.has(row.decisionId)) fail("alert input missing"); });
  data.reviews.forEach((row) => { if (!alert.has(row.alertId)) fail("review alert missing"); });
  data.briefs.forEach((row) => { if (row.alertIds.some((id) => !alert.has(id))) fail("brief alert missing"); });
  data.exports.forEach((row) => { if (!brief.has(row.briefId)) fail("export brief missing"); });
  return data;
}
