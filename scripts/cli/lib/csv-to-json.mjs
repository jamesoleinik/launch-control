// Convert a parsed CSV row + YAML mapping → Dataverse-ready JSON payload.
//
// Handles type coercion plus inline provenance (`lc_sourcefile`, `lc_ingestedat`,
// `lc_rawjson`). Field-level renames between the YAML mapping and the actual
// env logical names are supplied via ctx.fieldOverrides.

function coerce(rawValue, type) {
  if (rawValue === undefined || rawValue === null) return undefined;
  const v = String(rawValue).trim();
  if (v === '') return undefined;

  switch (type) {
    case 'string':
    case 'memo':
    case 'choice': // env stores choices as plain strings on staging tables
      return v;
    case 'integer':
      return parseInt(v, 10);
    case 'decimal':
      return Number(v);
    case 'boolean':
      return /^(true|1|yes|y)$/i.test(v);
    case 'date':
    case 'datetime': {
      if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return `${v}T00:00:00Z`;
      return new Date(v).toISOString();
    }
    default:
      return v;
  }
}

/**
 * Build the Dataverse JSON payload for one CSV row.
 * @param {object} mapping            - one entry from unified_mapping.yaml mappings[]
 * @param {object} row                - parsed CSV row (header → string)
 * @param {object} ctx                - { sourceFilename, ingestedAt, fieldOverrides }
 * @param {object} ctx.fieldOverrides - yaml schema → env logical name (e.g. { lc_SourceRowId: 'lc_sourceid' })
 */
export function buildRowPayload(mapping, row, ctx) {
  const payload = {};
  const overrides = ctx.fieldOverrides ?? {};

  for (const [srcCol, fieldDef] of Object.entries(mapping.fields)) {
    const targetLogical = overrides[fieldDef.schema] ?? fieldDef.schema.toLowerCase();
    const val = coerce(row[srcCol], fieldDef.type);
    if (val !== undefined) payload[targetLogical] = val;
  }

  // Inline provenance fields present on every lc_stg_tracker_* table.
  payload.lc_sourcefile = ctx.sourceFilename;
  payload.lc_ingestedat = ctx.ingestedAt;
  payload.lc_rawjson = JSON.stringify(row);

  return payload;
}
