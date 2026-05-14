// Upload every business skill in `business-skills/*.md` to Dataverse as
// records on the `skill` table. Replaces `dataverse skill upload --all`,
// which is broken in CLI v1.0.31 (AOT JSON reflection bug in
// SkillUploadCommand.CallUploadBusinessSkillAsync). The `skill` entity is a
// regular table, so we go through `data create` / `data update` instead.

import fs from 'node:fs';
import path from 'node:path';
import {
  repoRoot,
  dvCli,
  dataCreate,
  dataUpdate,
  logHeader,
  logStep,
  logOk,
  logFail,
} from './lib/dv.mjs';

const SKILLS_DIR = path.join(repoRoot, 'business-skills');
const ENTITY_SET = 'skills';

function parseMarkdown(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split(/\r?\n/);
  const titleLine = lines.find((l) => l.startsWith('# ')) ?? '';
  const name = titleLine.replace(/^#\s*/, '').trim() || path.basename(filePath, '.md');

  let description = '';
  const descMatch = content.match(/^## Description\s*\n([\s\S]+?)(?:\n## |\n*$)/m);
  if (descMatch) description = descMatch[1].trim();

  const base = path.basename(filePath, '.md').replace(/[^a-zA-Z0-9]/g, '_');
  const uniquename = `lc_${base}`;

  return { name, description: description.slice(0, 2000), body: content, uniquename };
}

function listExistingSkills() {
  const r = dvCli([
    'data',
    'query',
    '--table',
    ENTITY_SET,
    '--select',
    'skillid,uniquename,name',
    '--json',
  ]);
  if (r.status !== 0) return new Map();
  try {
    const text = (r.stdout || '').trim();
    const i = text.indexOf('[');
    const j = text.indexOf('{');
    const start = i === -1 ? j : j === -1 ? i : Math.min(i, j);
    if (start < 0) return new Map();
    const parsed = JSON.parse(text.slice(start));
    const rows = Array.isArray(parsed) ? parsed : parsed.value ?? [];
    const map = new Map();
    for (const row of rows) {
      if (row.uniquename) map.set(row.uniquename, row.skillid);
    }
    return map;
  } catch {
    return new Map();
  }
}

function main() {
  logHeader('Launch Control — Business Skills upload');

  if (!fs.existsSync(SKILLS_DIR)) {
    logFail(`Skills directory not found: ${SKILLS_DIR}`);
    process.exit(1);
  }

  const files = fs
    .readdirSync(SKILLS_DIR)
    .filter((f) => f.endsWith('.md'))
    .map((f) => path.join(SKILLS_DIR, f))
    .sort();

  if (files.length === 0) {
    logFail('No .md skill files found.');
    process.exit(1);
  }

  logStep(`Discovered ${files.length} skill file(s) in business-skills/`);
  logStep('Reading existing skills from Dataverse…');
  const existing = listExistingSkills();
  logOk(`Existing skills in env: ${existing.size}`);

  let created = 0;
  let updated = 0;
  let failed = 0;

  for (const file of files) {
    const skill = parseMarkdown(file);
    const label = path.basename(file);
    const payload = {
      name: skill.name,
      description: skill.description,
      body: skill.body,
      uniquename: skill.uniquename,
      ispersonal: false,
    };

    const existingId = existing.get(skill.uniquename);
    if (existingId) {
      const r = dataUpdate(ENTITY_SET, existingId, payload);
      if (r.ok) {
        logOk(`${label} → updated (${skill.uniquename})`);
        updated++;
      } else {
        logFail(`${label} → update FAILED: ${(r.stderr || r.stdout || '').trim().slice(0, 300)}`);
        failed++;
      }
    } else {
      const r = dataCreate(ENTITY_SET, payload);
      if (r.ok) {
        logOk(`${label} → created (${skill.uniquename} = ${r.id})`);
        created++;
      } else {
        logFail(`${label} → create FAILED: ${(r.stderr || r.stdout || '').trim().slice(0, 300)}`);
        failed++;
      }
    }
  }

  logHeader('Summary');
  console.log(`  Created: ${created}`);
  console.log(`  Updated: ${updated}`);
  console.log(`  Failed:  ${failed}`);
  process.exit(failed === 0 ? 0 : 1);
}

main();
