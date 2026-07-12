#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(process.argv[2] ?? process.cwd());
const packagePath = resolve(root, "package.json");

if (!existsSync(packagePath)) {
  console.log(JSON.stringify({ root, react: null, typescript: null, accepted: false, reason: "package.json not found" }));
  process.exit(0);
}

const pkg = JSON.parse(readFileSync(packagePath, "utf8"));
const dependencies = {
  ...(pkg.dependencies ?? {}),
  ...(pkg.devDependencies ?? {}),
  ...(pkg.peerDependencies ?? {}),
};

const react = dependencies.react ?? null;
const typescript = dependencies.typescript ?? null;
const accepted = typeof react === "string"
  && /(^|[^0-9])19\.2(?:\.|[^0-9]|$)/.test(react)
  && typeof typescript === "string"
  && /(^|[^0-9])7(?:\.|[^0-9]|$)/.test(typescript);

console.log(JSON.stringify({
  root,
  react,
  typescript,
  accepted,
  acceptanceTarget: { react: "19.2", typescript: "7" },
  warning: accepted ? null : "Other React and TypeScript versions may not work; require explicit confirmation.",
}, null, 2));
