#!/usr/bin/env node
// Episode 2 — Mapping-driven ingestion via the Dataverse CLI.
//
// Reads datamodel/mappings/unified_mapping.yaml and the matching
// datamodel/samples/*.csv files, then drives `dataverse data create`
// for each row into its staging table. Provenance is captured via a
// single lc_ImportRun (and an lc_SourceFile per CSV processed).

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import YAML from 'yaml';
import { parse as csvParse } from 'csv-parse/sync';

import {
  repoRoot,
  loadEnv,
  dataCreate,
  dataUpdate,
  fetchOptionMap,
  logHeader,
  logStep,
  logOk,
  logFail,
} from './lib/dv.mjs';
import { buildRowPayload } from './lib/csv-to-json.mjs';

const STATUS = { Pending: 10600050, Running: 10600051, Succeeded: 10600052, Failed: 10600053 };

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

// Resolve entity-set names per logical name (auto-pluralization is unreliable).
// We hard-code the discovered set names — they're stable per environment.
const ENTITY_SETS = {
  lc_trackera: 'lc_trackeras',
  lc_trackerb: 'lc_trackerbs',
  lc_trackerc: 'lc_trackercs',
  lc_trackerd: 'lc_trackerds',
  lc_trackere: 'lc_trackeres',
  lc_importrun: 'lc_importruns',
  lc_sourcefile: 'lc_sourcefiles',
};

logStep('Fetching choice option metadata for picklists…');
const choiceMaps = {};
for (const m of mapping.mappings) {
  const entityLogical = m.target_entity.toLowerCase();
  for (const f of Object.values(m.fields)) {
    if (f.type !== 'choice') continue;
    const attrLogical = f.schema.toLowerCase();
    const cacheKey = `${entityLogical}:${attrLogical}`;
    if (choiceMaps[cacheKey]) continue;
    const map = fetchOptionMap(entityLogical, attrLogical);
    if (!map) {
      logFail(`Could not fetch options for ${entityLogical}.${attrLogical}`);
      process.exit(3);
    }
    choiceMaps[cacheKey] = map;
  }
}
logOk(`Cached option sets for ${Object.keys(choiceMaps).length} choice fields`);

// 1. Create lc_ImportRun (Status=Running)
const runStartedAt = new Date().toISOString();
const runName = `Ep2 CLI ingest ${runStartedAt.slice(0, 19).replace('T', ' ')} UTC`;
logStep(`Creating lc_importrun: ${runName}`);
const importRunRes = dataCreate(ENTITY_SETS.lc_importrun, {
  lc_name: runName,
  lc_startedat: runStartedAt,
  lc_status: STATUS.Running,
  lc_recordsprocessed: 0,
  lc_notes: 'Created by scripts/cli/ingest.mjs',
});
if (!importRunRes.ok || !importRunRes.id) {
  logFail(`lc_importrun create failed: ${importRunRes.stderr || importRunRes.parseError}`);
  process.exit(4);
}
const importRunId = importRunRes.id;
logOk(`lc_importrun created: ${importRunId}`);

// 2. Process each tracker
let totalRows = 0;
const summary = [];

for (const m of mapping.mappings) {
  const entityLogical = m.target_entity.toLowerCase();
  const entitySet = ENTITY_SETS[entityLogical];
  if (!entitySet) {
    logFail(`No entity-set mapping for ${entityLogical}`);
    continue;
  }

  const csvPath = path.join(samplesDir, m.source);
  if (!fs.existsSync(csvPath)) {
    logFail(`Missing CSV: ${csvPath}`);
    continue;
  }

  logHeader(`Tracker → ${m.display_name} (${entitySet})`);
  const rawCsv = fs.readFileSync(csvPath, 'utf8');
  const rows = csvParse(rawCsv, { columns: true, skip_empty_lines: true, trim: true });
  logStep(`${rows.length} row(s) from ${m.source}`);

  // Compute file checksum
  const checksum = crypto.createHash('sha256').update(rawCsv).digest('hex').slice(0, 32);

  // Create lc_SourceFile linked to importrun
  const sourceSystem = m.source.replace(/\.sample\.csv$/, '');
  const sfRes = dataCreate(ENTITY_SETS.lc_sourcefile, {
    lc_name: m.source,
    lc_filename: m.source,
    lc_checksum: checksum,
    lc_rowcount: rows.length,
    'lc_ImportRunId@odata.bind': `/lc_importruns(${importRunId})`,
  });
  if (!sfRes.ok) {
    logFail(`lc_sourcefile create failed for ${m.source}: ${sfRes.stderr}`);
    continue;
  }
  logOk(`lc_sourcefile created: ${sfRes.id}`);

  // Insert each row
  let inserted = 0;
  for (const row of rows) {
    let payload;
    try {
      payload = buildRowPayload(m, row, {
        importRunId,
        sourceSystem,
        sourceFilename: m.source,
        choiceMaps,
        entityLogical,
      });
    } catch (e) {
      logFail(`Row coerce error for ${m.source}: ${e.message}`);
      continue;
    }
    const r = dataCreate(entitySet, payload);
    if (!r.ok) {
      logFail(`Row insert failed: ${r.stderr || r.parseError}`);
      continue;
    }
    inserted++;
    totalRows++;
    logOk(`  ↳ ${row.id ?? '?'} → ${r.id}`);
  }
  summary.push({ tracker: m.display_name, inserted, total: rows.length });
}

// 3. Finalize importrun
logHeader('Finalizing import run');
const finalize = dataUpdate(ENTITY_SETS.lc_importrun, importRunId, {
  lc_status: STATUS.Succeeded,
  lc_recordsprocessed: totalRows,
  lc_notes: `Inserted ${totalRows} row(s) across ${summary.length} tracker(s).`,
});
if (!finalize.ok) {
  logFail(`finalize failed: ${finalize.stderr}`);
  process.exit(5);
}
logOk(`lc_importrun marked Succeeded (records=${totalRows})`);

console.log('');
console.log('Summary:');
for (const s of summary) console.log(`  ${s.tracker}: ${s.inserted}/${s.total}`);
console.log('');
console.log(`ImportRun ID: ${importRunId}`);
console.log('Verify:');
console.log(`  npx -y @microsoft/dataverse@latest data query --sql "SELECT lc_name, lc_recordsprocessed, lc_statusname FROM lc_importrun WHERE lc_importrunid = '${importRunId}'"`);
