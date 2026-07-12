#!/usr/bin/env node

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const testsDir = dirname(fileURLToPath(import.meta.url));
const checkDir = resolve(testsDir, "..");
const result = spawnSync("ast-grep", [
  "scan",
  "-r",
  resolve(checkDir, "rule.yml"),
  testsDir,
  "--json=compact",
], { encoding: "utf8" });

assert.equal(result.error, undefined, result.error?.message);
assert.equal(result.status, 1, result.stderr);

const findings = JSON.parse(result.stdout || "[]");
const files = findings.map((finding) => finding.file.replaceAll("\\", "/").split("/").at(-1)).sort();

assert.deepEqual(files, [
  "invalid-arrow.tsx",
  "invalid-custom-root.tsx",
  "invalid-function.tsx",
  "invalid-unused-call.tsx",
]);
assert.equal(findings.length, 4);
for (const finding of findings) {
  assert.equal(finding.ruleId, "require-ui-state-props");
  assert.equal(finding.severity, "error");
  assert.equal(
    finding.message,
    "@ui-inspectable component must attach uiStateProps(...) to rendered JSX",
  );
  assert.equal(finding.text, "/** @ui-inspectable */");
  assert.deepEqual(finding.range.start, { line: 0, column: 0 });
}
console.log("require-ui-state-props fixtures passed");
