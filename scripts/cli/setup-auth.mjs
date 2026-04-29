#!/usr/bin/env node
// Episode 2 — Set up Dataverse CLI auth profile.
// Reads DATAVERSE_URL from .env, runs `dataverse auth create` interactively.
// Idempotent: if a profile already exists for the URL, we skip.

import { dvCli, dvCliJson, loadEnv, logHeader, logStep, logOk, logFail } from './lib/dv.mjs';

logHeader('Launch Control — Dataverse CLI auth setup');

const env = loadEnv();
const url = process.env.DATAVERSE_URL || env.DATAVERSE_URL;
if (!url) {
  logFail('DATAVERSE_URL not set in .env or environment.');
  process.exit(2);
}
logStep(`Target environment: ${url}`);

const list = dvCliJson(['auth', 'list']);
const existing = (Array.isArray(list.data) ? list.data : list.data?.profiles ?? [])
  .filter((p) => (p.environmentUrl || p.url || '').replace(/\/$/, '') === url.replace(/\/$/, ''));

if (existing.length > 0) {
  logOk(`Auth profile already exists for ${url} — skipping create.`);
  process.exit(0);
}

logStep('No matching profile — launching `dataverse auth create` (browser will open)…');
const create = dvCli(['auth', 'create', '--environment', url], { stdio: 'inherit' });
if (create.status !== 0) {
  logFail(`auth create failed (exit ${create.status}).`);
  process.exit(create.status || 1);
}
logOk('Auth profile created.');
