"use client";

import { useState } from "react";
import { putTableMapping } from "@/lib/api/client";
import type { SourceSummary, TableMapping } from "@/lib/api/client";

const SHEET = "application/vnd.google-apps.spreadsheet";
const newColumn = () => ({ header: "", predicate: "", type: "date" as const, unit: null as string | null, enum_values: null as string[] | null });

export function TableMappingForm({ projectId, source, onSaved }: { projectId: string; source: SourceSummary; onSaved: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mapping, setMapping] = useState<TableMapping>(source.table_mapping ?? {
    sheet_name: null, a1_range: null, header_row: 1, row_business_key: "", columns: [newColumn()],
  });

  function updateColumn(index: number, update: Partial<TableMapping["columns"][number]>) {
    setMapping((current) => ({ ...current, columns: current.columns.map((column, i) => i === index ? { ...column, ...update } : column) }));
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(null);
    try {
      await putTableMapping(projectId, source.id, mapping);
      await onSaved();
      setOpen(false);
    } catch (value) {
      setError(value instanceof Error ? value.message : "Mapping could not be saved.");
    } finally { setBusy(false); }
  }

  return <div className="table-mapping">
    <button className="button button--secondary" type="button" onClick={() => setOpen(!open)}>{open ? "Close mapping" : source.status === "mapping_required" ? "Map table columns" : "Edit table mapping"}</button>
    {open && <form onSubmit={(event) => void save(event)} className="workspace-stack">
      <p className="field-help">The row key must match the monitored entity ID. Each typed column publishes a confirmed fact with its cell address.</p>
      {source.mime_type === SHEET && <div className="form-grid form-grid--two">
        <label className="form-field">Sheet name<input className="form-control" required value={mapping.sheet_name ?? ""} onChange={(event) => setMapping({ ...mapping, sheet_name: event.target.value })} placeholder="Updates" /></label>
        <label className="form-field">A1 range<input className="form-control" required value={mapping.a1_range ?? ""} onChange={(event) => setMapping({ ...mapping, a1_range: event.target.value.toUpperCase() })} placeholder="A1:D100" /></label>
      </div>}
      <div className="form-grid form-grid--two">
        <label className="form-field">Header row<input className="form-control" type="number" min="1" required value={mapping.header_row} onChange={(event) => setMapping({ ...mapping, header_row: Number(event.target.value) })} /></label>
        <label className="form-field">Row key header<input className="form-control" required value={mapping.row_business_key} onChange={(event) => setMapping({ ...mapping, row_business_key: event.target.value })} placeholder="Entity ID" /></label>
      </div>
      {mapping.columns.map((column, index) => <div className="form-grid form-grid--two" key={index}>
        <label className="form-field">Column header<input className="form-control" required value={column.header} onChange={(event) => updateColumn(index, { header: event.target.value })} placeholder="Delivery date" /></label>
        <label className="form-field">Fact predicate<input className="form-control" required value={column.predicate} onChange={(event) => updateColumn(index, { predicate: event.target.value })} placeholder="delivery_date" /></label>
        <label className="form-field">Value type<select className="form-control" value={column.type} onChange={(event) => updateColumn(index, { type: event.target.value as typeof column.type })}><option value="date">Date</option><option value="decimal">Decimal</option><option value="enum">Status</option></select></label>
        {column.type === "decimal" && <label className="form-field">Unit<input className="form-control" required value={column.unit ?? ""} onChange={(event) => updateColumn(index, { unit: event.target.value })} placeholder="USD" /></label>}
        {column.type === "enum" && <label className="form-field">Allowed values, comma separated<input className="form-control" required value={column.enum_values?.join(", ") ?? ""} onChange={(event) => updateColumn(index, { enum_values: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} placeholder="planned, delayed" /></label>}
        {mapping.columns.length > 1 && <button className="button button--secondary" type="button" onClick={() => setMapping((current) => ({ ...current, columns: current.columns.filter((_, i) => i !== index) }))}>Remove column</button>}
      </div>)}
      <div className="fact-card__actions"><button className="button button--secondary" type="button" disabled={mapping.columns.length >= 20} onClick={() => setMapping((current) => ({ ...current, columns: [...current.columns, newColumn()] }))}>Add typed column</button><button className="button button--primary" type="submit" disabled={busy}>{busy ? "Checking table…" : "Save and ingest"}</button></div>
      {error && <p role="alert" className="notice notice--error">{error}</p>}
    </form>}
  </div>;
}
