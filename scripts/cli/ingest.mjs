#!/usr/bin/env node
// Episode 2 — Mapping-driven ingestion via the Dataverse CLI.
//
// Reads datamodel/mappings/unified_mapping.yaml and the matching
// datamodel/samples/*.csv files, then drives `dataverse data create`
// for each row into its staging table.
//
// This env uses the unified data model from the lc-datamodel skill:
//   - Tables are named `lc_stg_tracker_a..e` (snake_case, _stg_ prefix), not
//     `lc_trackera..e`. The ENTITY_OVERRIDES map translates.
//   - There are NO `lc_importrun` / `lc_sourcefile` lookup tables. Provenance
//     is captured inline on each staging row via `lc_sourcefile` (string =
//     filename), `lc_ingestedat` (datetime), and `lc_rawjson` (full source row
//     as JSON). The script writes a console summary in place of the import-run
//     record.
//   - `lc_priority` / `lc_status` are plain Strings in this env, not Picklists,
//     so the script does NOT fetch option-set metadata.
//
// Field-level renames (yaml schema → env logical name) live in FIELD_OVERRIDES
// keyed by mapping.target_entity.

import fs from 'node:fs';
import path from 'node:path';
import YAML from 'yaml';
import { parse as csvParse } from 'csv-parse/sync';

import {
  repoRoot,
  loadEnv,
  dataCreate,
  logHeader,
  logStep,
  logOk,
  logFail,
} from './lib/dv.mjs';
import { buildRowPayload } from './lib/csv-to-json.mjs';

logHeader('Launch Control — Episode 2 ingestion');

const env = loadEnv();
const dvUrl = process.env.DATAVERSE_URL || env.DATAVERSE_URL;
if (!dvUrl) {
  logFail('DATAVERSE_URL not set in .env.');
  process.exit(2);
}
logStep(`Target: ${dvUrl}`);

const mappingPath = path.join(repoRoot, 'datamodel', 'mappings', 'unified_mapping.yaml');
const samplesDir = path.join(repoRoot, 'datamodel', 'samples');
const mapping = YAML.parse(fs.readFileSync(mappingPath, 'utf8'));
logOk(`Loaded ${mapping.mappings.length} mapping(s) from unified_mapping.yaml`);

// Entity-set overrides: yaml target_entity → { logicalName, entitySetName }.
// The env uses the lc-datamodel staging convention (`lc_stg_tracker_a..e`),
// not the legacy `lc_trackera..e` form the yaml uses.
const ENTITY_OVERRIDES = {
  lc_TrackerA: { logicalName: 'lc_stg_tracker_a', entitySetName: 'lc_stg_tracker_as' },
  lc_TrackerB: { logicalName: 'lc_stg_tracker_b', entitySetName: 'lc_stg_tracker_bs' },
  lc_TrackerC: { logicalName: 'lc_stg_tracker_c', entitySetName: 'lc_stg_tracker_cs' },
  lc_TrackerD: { logicalName: 'lc_stg_tracker_d', entitySetName: 'lc_stg_tracker_ds' },
  lc_TrackerE: { logicalName: 'lc_stg_tracker_e', entitySetName: 'lc_stg_tracker_es' },
};

// Per-tracker field renames: yaml `schema` → env logical name.
// Anything not listed falls through as lowercase(schema).
const FIELD_OVERRIDES = {
  lc_TrackerA: { lc_SourceRowId: 'lc_sourceid', lc_Milestone: 'lc_milestonename' },
  lc_TrackerB: { lc_SourceRowId: 'lc_sourceid', lc_Milestone: 'lc_milestonename', lc_Title: 'lc_name' },
  lc_TrackerC: { lc_SourceRowId: 'lc_sourceid' },
  lc_TrackerD: { lc_SourceRowId: 'lc_sourceid', lc_Milestone: 'lc_milestonename' },
  lc_TrackerE: { lc_SourceRowId: 'lc_sourceid' },
};

// Process each tracker
const runStartedAt = new Date().toISOString();
const runLabel = `Ep2 CLI ingest ${runStartedAt.slice(0, 19).replace('T', ' ')} UTC`;
logStep(`Run label: ${runLabel}`);

let totalRows = 0;
const summary = [];

for (const m of mapping.mappings) {
  const override = ENTITY_OVERRIDES[m.target_entity];
  if (!override) {
    logFail(`No entity-set override for ${m.target_entity}`);
    continue;
  }
  const { logicalName: entityLogical, entitySetName: entitySet } = override;

  const csvPath = path.join(samplesDir, m.source);
  if (!fs.existsSync(csvPath)) {
    logFail(`Missing CSV: ${csvPath}`);
    continue;
  }

  logHeader(`Tracker → ${m.display_name} (${entitySet})`);
  const rawCsv = fs.readFileSync(csvPath, 'utf8');
  const rows = csvParse(rawCsv, { columns: true, skip_empty_lines: true, trim: true });
  logStep(`${rows.length} row(s) from ${m.source}`);

  // Insert each row
  let inserted = 0;
  for (const row of rows) {
    let payload;
    try {
      payload = buildRowPayload(m, row, {
        sourceFilename: m.source,
        ingestedAt: runStartedAt,
        fieldOverrides: FIELD_OVERRIDES[m.target_entity] ?? {},
      });
    } catch (e) {
      logFail(`Row coerce error for ${m.source}: ${e.message}`);
      continue;
    }
    const r = dataCreate(entitySet, payload);
    if (!r.ok) {
      logFail(`Row insert failed: ${(r.stderr || r.stdout || r.parseError || '').trim().slice(0, 300)}`);
      continue;
    }
    inserted++;
    totalRows++;
    logOk(`  ↳ ${row.id ?? '?'} → ${r.id}`);
  }
  summary.push({ tracker: m.display_name, inserted, total: rows.length });
}

logHeader('Summary');
console.log(`  Run label: ${runLabel}`);
for (const s of summary) console.log(`  ${s.tracker}: ${s.inserted}/${s.total}`);
console.log(`  Total inserted: ${totalRows}`);
console.log('');
console.log('Verify:');
console.log(`  dataverse data query --table lc_stg_tracker_as --select lc_sourceid,lc_title,lc_ingestedat`);

