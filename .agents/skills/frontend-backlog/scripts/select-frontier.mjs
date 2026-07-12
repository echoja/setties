#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const ledgerPath = resolve(process.argv[2] ?? ".ui-quality/findings.jsonl");
if (!existsSync(ledgerPath)) {
  console.log("null");
  process.exit(0);
}

const findings = readFileSync(ledgerPath, "utf8")
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line, index) => {
    try {
      return JSON.parse(line);
    } catch (error) {
      throw new Error(`Invalid JSON on ${ledgerPath}:${index + 1}: ${error.message}`);
    }
  });

const open = findings.filter((finding) => finding.status === "open");
const openFingerprints = new Set(open.map((finding) => finding.fingerprint));
const eligible = open.filter((finding) =>
  !(finding.blocked_by ?? []).some((fingerprint) => openFingerprints.has(fingerprint))
);

const impact = { critical: 4, high: 3, medium: 2, low: 1 };
const severity = { P0: 4, P1: 3, P2: 2, P3: 1 };
const confidence = { high: 3, medium: 2, low: 1 };
const effort = { small: 1, medium: 2, large: 3 };

eligible.sort((a, b) =>
  (b.prerequisite_depth ?? 0) - (a.prerequisite_depth ?? 0)
  || (b.downstream_count ?? 0) - (a.downstream_count ?? 0)
  || (impact[b.user_impact] ?? 0) - (impact[a.user_impact] ?? 0)
  || (severity[b.severity] ?? 0) - (severity[a.severity] ?? 0)
  || (confidence[b.confidence] ?? 0) - (confidence[a.confidence] ?? 0)
  || (effort[a.estimated_effort] ?? 99) - (effort[b.estimated_effort] ?? 99)
  || String(a.observed_at ?? "").localeCompare(String(b.observed_at ?? ""))
);

console.log(JSON.stringify(eligible[0] ?? null, null, 2));
