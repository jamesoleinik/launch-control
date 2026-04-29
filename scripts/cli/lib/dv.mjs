// Shared helpers for Launch Control CLI scripts.
// Wraps `npx @microsoft/dataverse@latest …` subprocess invocation in a
// way that handles Windows path quoting reliably.

import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

export const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  '..'
);

export function loadEnv() {
  const envPath = path.join(repoRoot, '.env');
  if (!fs.existsSync(envPath)) return {};
  const out = {};
  for (const raw of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const idx = line.indexOf('=');
    out[line.slice(0, idx).trim()] = line
      .slice(idx + 1)
      .trim()
      .replace(/^"(.*)"$/, '$1');
  }
  return out;
}

function quoteArg(a) {
  // Quote anything that's not strictly safe — cmd.exe treats &, |, <, >, ^, (, )
  // and others as control chars, so we must wrap them.
  if (a === '' || /[^A-Za-z0-9_\-./:@]/.test(a)) {
    return `"${String(a).replace(/(["\\])/g, '\\$1')}"`;
  }
  return a;
}

export function dvCli(args, opts = {}) {
  const isWin = process.platform === 'win32';
  const fullArgs = ['-y', '@microsoft/dataverse@latest', ...args];
  // Node 20+ refuses to spawn .cmd/.bat without shell:true on Windows.
  // Use shell:true and pre-quote args ourselves.
  const cmdLine = isWin
    ? ['npx', ...fullArgs].map(quoteArg).join(' ')
    : 'npx';
  const cmdArgs = isWin ? [] : fullArgs;
  const result = spawnSync(cmdLine, cmdArgs, {
    encoding: 'utf8',
    shell: true,
    ...opts,
  });
  return {
    status: result.status ?? -1,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
    error: result.error,
  };
}

export function dvCliJson(args, opts = {}) {
  const r = dvCli([...args, '--json'], opts);
  if (r.status !== 0) return { ok: false, ...r, data: null };
  try {
    const text = (r.stdout || '').trim();
    const start = text.indexOf('{');
    const startArr = text.indexOf('[');
    const jsonStart =
      start === -1 ? startArr : startArr === -1 ? start : Math.min(start, startArr);
    const jsonText = jsonStart >= 0 ? text.slice(jsonStart) : text;
    return { ok: true, ...r, data: JSON.parse(jsonText) };
  } catch (e) {
    return { ok: false, ...r, data: null, parseError: e.message };
  }
}

/**
 * Make a Dataverse Web API call via `dataverse api request --target dataverse`.
 * Returns parsed JSON or null on failure.
 */
export function dvApi(method, apiPath) {
  const r = dvCli([
    'api',
    'request',
    '--target',
    'dataverse',
    '--method',
    method,
    '--path',
    apiPath,
  ]);
  if (r.status !== 0) {
    return { ok: false, ...r, data: null };
  }
  try {
    const text = (r.stdout || '').trim();
    const i = text.indexOf('{');
    return { ok: true, ...r, data: i >= 0 ? JSON.parse(text.slice(i)) : null };
  } catch (e) {
    return { ok: false, ...r, data: null, parseError: e.message };
  }
}

/**
 * Fetch a label→optionValue map for a Picklist attribute on an entity.
 */
export function fetchOptionMap(entityLogical, attributeLogical) {
  const path = `/api/data/v9.2/EntityDefinitions(LogicalName='${entityLogical}')/Attributes(LogicalName='${attributeLogical}')/Microsoft.Dynamics.CRM.PicklistAttributeMetadata?$expand=OptionSet($select=Options)&$select=LogicalName`;
  const r = dvApi('GET', path);
  if (!r.ok || !r.data?.OptionSet?.Options) return null;
  const map = {};
  for (const opt of r.data.OptionSet.Options) {
    const label = opt.Label?.UserLocalizedLabel?.Label;
    if (label) map[label] = opt.Value;
  }
  return map;
}

/**
 * Create a record via `data create` and return the new GUID.
 * Uses --return + --json so we can capture the row back.
 */
export function dataCreate(entitySetName, payloadObj) {
  const tmp = path.join(
    repoRoot,
    'scripts',
    'cli',
    `.tmp-create-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.json`
  );
  fs.writeFileSync(tmp, JSON.stringify(payloadObj));
  try {
    const r = dvCli([
      'data',
      'create',
      '--table',
      entitySetName,
      '--data-file',
      tmp,
      '--return',
      '--json',
    ]);
    if (r.status !== 0) {
      return { ok: false, ...r, id: null };
    }
    // parse JSON from stdout
    const text = (r.stdout || '').trim();
    const i = text.indexOf('{');
    if (i < 0) return { ok: false, ...r, id: null, parseError: 'no JSON found' };
    try {
      const obj = JSON.parse(text.slice(i));
      // Find the primary id field — looks like <logicalname>id
      const idKey = Object.keys(obj).find((k) => /^[a-z_]+id$/.test(k) && obj[k]);
      const id = idKey ? obj[idKey] : null;
      return { ok: true, ...r, id, record: obj };
    } catch (e) {
      return { ok: false, ...r, id: null, parseError: e.message };
    }
  } finally {
    try { fs.unlinkSync(tmp); } catch {}
  }
}

/**
 * Update a record via `data update`.
 */
export function dataUpdate(entitySetName, id, payloadObj) {
  const tmp = path.join(
    repoRoot,
    'scripts',
    'cli',
    `.tmp-update-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.json`
  );
  fs.writeFileSync(tmp, JSON.stringify(payloadObj));
  try {
    const r = dvCli([
      'data',
      'update',
      '--table',
      entitySetName,
      '--id',
      id,
      '--data-file',
      tmp,
    ]);
    return { ok: r.status === 0, ...r };
  } finally {
    try { fs.unlinkSync(tmp); } catch {}
  }
}

export function logHeader(text) {
  console.log('');
  console.log(`\x1b[36m=== ${text} ===\x1b[0m`);
}

export function logStep(text) {
  console.log(`\x1b[33m→\x1b[0m ${text}`);
}

export function logOk(text) {
  console.log(`\x1b[32m✔\x1b[0m ${text}`);
}

export function logFail(text) {
  console.log(`\x1b[31m✖\x1b[0m ${text}`);
}
