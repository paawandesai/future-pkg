// Writes dist/third-party-notices.txt after `vite build`: every production dependency of the site
// (from `pnpm licenses list --prod`, so it follows the lockfile) with the licence text it ships.
// The minified bundle drops licence comments, and the IBM Plex fonts need their OFL text alongside.
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(web, "dist", "third-party-notices.txt");
const LICENCE_FILE = /^(licen[cs]e|copying|notice)(\..*)?$/i;

const raw = execFileSync("pnpm", ["licenses", "list", "--json", "--prod"], { cwd: web, encoding: "utf8" });
const packages = [];
for (const [licence, pkgs] of Object.entries(JSON.parse(raw))) {
  for (const p of pkgs) {
    // Type-only packages never reach the bundle.
    if (p.name.startsWith("@types/") || p.name === "csstype") continue;
    p.versions.forEach((version, i) => packages.push({ ...p, version, path: p.paths[i], licence }));
  }
}
packages.sort((a, b) => a.name.localeCompare(b.name) || a.version.localeCompare(b.version));

const rule = "=".repeat(78);
const parts = [
  "Third-party software in this site\n\n" +
    "The coach decision support demo bundles the open-source packages below. Each entry gives the\n" +
    "package, its version and licence, and the licence text the package ships. Generated at build\n" +
    "time from the lockfile (web production dependencies).\n",
];
for (const p of packages) {
  const files =
    p.path && existsSync(p.path)
      ? readdirSync(p.path)
          .filter((f) => LICENCE_FILE.test(f))
          .sort()
      : [];
  const texts = files.map((f) => readFileSync(join(p.path, f), "utf8").trim());
  const head = [`${p.name} ${p.version}`, `Licence: ${p.licence}`];
  if (p.homepage) head.push(`Homepage: ${p.homepage}`);
  if (texts.length === 0) {
    if (!p.licence) throw new Error(`${p.name} ${p.version}: no licence metadata and no licence file`);
    texts.push(`(The package ships no licence file; its package metadata declares ${p.licence}.)`);
  }
  parts.push(`${rule}\n${head.join("\n")}\n${rule}\n\n${texts.join("\n\n")}\n`);
}
writeFileSync(out, parts.join("\n"));
process.stdout.write(`third-party notices: ${packages.length} packages -> dist/third-party-notices.txt\n`);
