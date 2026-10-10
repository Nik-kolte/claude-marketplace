#!/usr/bin/env node
// Read-only Axiom APL query helper for the `debug` agent. Zero dependencies (Node >= 18, global fetch).
//
//   node axiom-query.mjs --token-var AXIOM_QUERY_TOKEN_PROD [--env-file <path>]... \
//        (--since 24h | --from <ISO> [--to <ISO>]) (--apl "<APL>" | --apl-file <file>) \
//        [--format table|json] [--max-rows 200] [--url https://api.axiom.co]
//
// The token is read from the environment, else from the env files (KEY=VALUE lines; default
// ~/.config/axiom/.env is always tried last). It is never printed. Only the APL query endpoint is
// called, so a query-only token is all this needs.

import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

function parseArgs(argv) {
  const a = { envFiles: [], format: "table", maxRows: 200, url: "https://api.axiom.co" };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => {
      const val = argv[++i];
      if (val === undefined) fail(`missing value for ${k}`);
      return val;
    };
    if (k === "--token-var") a.tokenVar = v();
    else if (k === "--env-file") a.envFiles.push(v());
    else if (k === "--since") a.since = v();
    else if (k === "--from") a.from = v();
    else if (k === "--to") a.to = v();
    else if (k === "--apl") a.apl = v();
    else if (k === "--apl-file") a.apl = readFileSync(v(), "utf8");
    else if (k === "--format") a.format = v();
    else if (k === "--max-rows") a.maxRows = Number(v());
    else if (k === "--url") a.url = v().replace(/\/+$/, "");
    else if (k === "-h" || k === "--help") usage(0);
    else fail(`unknown argument ${k}`);
  }
  return a;
}

function usage(code) {
  console.log(readFileSync(new URL(import.meta.url), "utf8").split("\n").slice(1, 11).join("\n").replace(/^\/\/ ?/gm, ""));
  process.exit(code);
}

function fail(msg) {
  console.error(`axiom-query: ${msg}`);
  process.exit(2);
}

function readToken(varName, envFiles) {
  if (process.env[varName]) return process.env[varName];
  const files = [...envFiles, join(homedir(), ".config", "axiom", ".env")];
  for (const f of files) {
    if (!existsSync(f)) continue;
    for (const line of readFileSync(f, "utf8").split(/\r?\n/)) {
      const m = line.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
      if (m && m[1] === varName) return m[2].replace(/^(['"])(.*)\1$/, "$2");
    }
  }
  return null;
}

const UNITS = { m: 60e3, h: 3600e3, d: 86400e3 };
function resolveRange(a) {
  if (a.since) {
    const m = a.since.match(/^(\d+)([mhd])$/);
    if (!m) fail(`--since must look like 30m, 6h or 2d (got ${a.since})`);
    const end = new Date();
    return { startTime: new Date(end - Number(m[1]) * UNITS[m[2]]).toISOString(), endTime: end.toISOString() };
  }
  if (a.from) {
    const s = new Date(a.from), e = a.to ? new Date(a.to) : new Date();
    if (isNaN(s) || isNaN(e)) fail("--from/--to must be ISO dates, e.g. 2026-10-08T00:00:00+05:30");
    return { startTime: s.toISOString(), endTime: e.toISOString() };
  }
  fail("give a time range: --since 24h, or --from <ISO> [--to <ISO>]");
}

function cell(v) {
  if (v === null || v === undefined) return "";
  const s = typeof v === "object" ? JSON.stringify(v) : String(v);
  return s.replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
}

// min()/max() of _time come back as float nanoseconds; show them as ISO like plain datetime columns.
function isTimeField(f) {
  return f.type === "datetime" || (["min", "max"].includes(f.agg?.name) && f.agg?.fields?.includes("_time"));
}
function timeCell(v) {
  if (typeof v !== "number") return v;
  const ms = v > 1e17 ? v / 1e6 : v; // ns -> ms
  return new Date(ms).toISOString();
}

function printTable(t, maxRows) {
  const names = t.fields.map((f) => f.name);
  const timeCols = t.fields.map(isTimeField);
  const nRows = t.columns.length ? t.columns[0].length : 0;
  console.log(`## rows: ${nRows}${nRows > maxRows ? ` (first ${maxRows} shown)` : ""}`);
  if (!nRows) return;
  console.log(`| ${names.join(" | ")} |`);
  console.log(`|${names.map(() => "---").join("|")}|`);
  for (let r = 0; r < Math.min(nRows, maxRows); r++) {
    console.log(`| ${t.columns.map((c, i) => cell(timeCols[i] ? timeCell(c[r]) : c[r])).join(" | ")} |`);
  }
}

const a = parseArgs(process.argv.slice(2));
if (!a.tokenVar) fail("--token-var is required (name of the env var holding a query-only token)");
if (!a.apl) fail("--apl or --apl-file is required");
const token = readToken(a.tokenVar, a.envFiles);
if (!token) fail(`token ${a.tokenVar} not found in the environment or env files (${[...a.envFiles, "~/.config/axiom/.env"].join(", ")})`);
const range = resolveRange(a);

let res;
try {
  res = await fetch(`${a.url}/v1/datasets/_apl?format=tabular`, {
    method: "POST",
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
    body: JSON.stringify({ apl: a.apl, ...range }),
    signal: AbortSignal.timeout(60_000),
  });
} catch (e) {
  fail(`request failed: ${e.name === "TimeoutError" ? "timeout after 60 s" : e.message}`);
}
const text = await res.text();
if (!res.ok) {
  let msg = text;
  try { msg = JSON.parse(text).message ?? text; } catch {}
  fail(`HTTP ${res.status}: ${String(msg).split(token).join("<token>").slice(0, 800)}`);
}
const body = JSON.parse(text);
if (a.format === "json") {
  console.log(JSON.stringify(body, null, 2));
} else {
  console.log(`range: ${range.startTime} -> ${range.endTime} (UTC)`);
  // `_totals` repeats the main table's aggregates without the time bins; skip it.
  for (const t of (body.tables ?? []).filter((t) => t.name !== "_totals")) printTable(t, a.maxRows);
  const st = body.status ?? {};
  if (st.isPartial) console.log("WARNING: partial result (Axiom cut the scan short); narrow the range or the query.");
  if (st.elapsedTime !== undefined) console.log(`elapsed: ${Math.round(st.elapsedTime / 1000)} ms, rows scanned: ${st.rowsExamined ?? "?"}`);
}
