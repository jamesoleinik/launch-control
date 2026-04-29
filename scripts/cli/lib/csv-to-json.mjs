// Convert a parsed CSV row + YAML mapping → Dataverse-ready JSON payload.
//
// Handles type coercion, choice → integer lookup, provenance fields,
// and the lc_ImportRunId@odata.bind lookup.

import crypto from 'node:crypto';

function coerce(rawValue, type, choiceMap) {
  if (rawValue === undefined || rawValue === null) return undefined;
  const v = String(rawValue).trim();
  if (v === '') return undefined;

  switch (type) {
    case 'string':
    case 'memo':
      return v;
    case 'integer':
      return parseInt(v, 10);
    case 'decimal':
      return Number(v);
    case 'boolean':
      return /^(true|1|yes|y)$/i.test(v);
    case 'date':
    case 'datetime': {
      // Dataverse expects ISO. CSV samples are YYYY-MM-DD; expand to UTC midnight.
      if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return `${v}T00:00:00Z`;
      return new Date(v).toISOString();
    }
    case 'choice': {
      if (!choiceMap) {
        throw new Error(`Missing choice metadata for value "${v}"`);
      }
      const ci = Object.entries(choiceMap).find(
        ([label]) => label.toLowerCase() === v.toLowerCase()
      );
      if (!ci) {
        throw new Error(
          `Choice value "${v}" not found. Known: ${Object.keys(choiceMap).join(', ')}`
        );
      }
      return ci[1];
    }
    default:
      return v;
  }
}

export function rowHash(rowObj) {
  const canonical = JSON.stringify(
    Object.keys(rowObj)
      .sort()
      .reduce((acc, k) => ((acc[k] = rowObj[k]), acc), {})
  );
  return crypto.createHash('sha256').update(canonical).digest('hex');
}

/**
 * Build the Dataverse JSON payload for one CSV row.
 * @param {object} mapping     - one entry from unified_mapping.yaml mappings[]
 * @param {object} row         - parsed CSV row (header → string)
 * @param {object} ctx         - { importRunId, sourceSystem, sourceFilename, choiceMaps }
 * @param {object} ctx.choiceMaps - { [logicalName]: { Label: optionValueInt } }
 */
export function buildRowPayload(mapping, row, ctx) {
  const payload = {};

  for (const [srcCol, fieldDef] of Object.entries(mapping.fields)) {
    const logical = fieldDef.schema.toLowerCase();
    const choiceMap =
      fieldDef.type === 'choice'
        ? ctx.choiceMaps[`${ctx.entityLogical}:${logical}`]
        : null;
    const val = coerce(row[srcCol], fieldDef.type, choiceMap);
    if (val !== undefined) payload[logical] = val;
  }

  payload.lc_sourcesystem = ctx.sourceSystem;
  payload.lc_sourcefilename = ctx.sourceFilename;
  payload.lc_sourcerowhash = rowHash(row);
  payload.lc_needsmanualreview = false;
  payload['lc_ImportRunId@odata.bind'] = `/lc_importruns(${ctx.importRunId})`;

  return payload;
}
