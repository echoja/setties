#!/usr/bin/env node

import { spawnSync } from "node:child_process";

function run(command, args) {
  return spawnSync(command, args, { encoding: "utf8" });
}

const ghVersion = run("gh", ["--version"]);
if (ghVersion.error || ghVersion.status !== 0) {
  console.error("GitHub CLI is required. Install and authenticate gh before auditing.");
  process.exit(2);
}

const auth = run("gh", ["auth", "status"]);
if (auth.status !== 0) {
  console.error(auth.stderr || "GitHub CLI is not authenticated.");
  process.exit(2);
}

const root = run("git", ["rev-parse", "--show-toplevel"]);
if (root.status !== 0) {
  console.error("The current directory is not inside a Git repository.");
  process.exit(2);
}

const repo = run("gh", ["repo", "view", "--json", "nameWithOwner,url"]);
if (repo.status !== 0) {
  console.error(repo.stderr || "The current Git repository is not accessible through GitHub CLI.");
  process.exit(2);
}

const issues = run("gh", [
  "issue",
  "list",
  "--state",
  "open",
  "--search",
  "label:frontend-quality",
  "--limit",
  "100",
  "--json",
  "number,title,url,labels",
]);
if (issues.status !== 0) {
  console.error(issues.stderr || "Unable to list GitHub issues.");
  process.exit(2);
}

const active = JSON.parse(issues.stdout).filter((issue) =>
  issue.labels.some((label) => label.name === "frontend-quality")
);

const result = {
  repository: JSON.parse(repo.stdout),
  gitRoot: root.stdout.trim(),
  activeIssues: active,
  accepted: active.length <= 1,
};

console.log(JSON.stringify(result, null, 2));

if (!result.accepted) {
  console.error("More than one open frontend-quality issue exists. Restore the single-frontier invariant before auditing.");
  process.exit(3);
}
