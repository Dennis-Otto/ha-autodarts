// What ESLint skips (eslint.config.mjs): every folder that .gitignore ignores, such as the
// cache of the website and the virtual environment of its preview, whose JavaScript is not
// ours and failed `bash scripts/check.sh` with thousands of errors, and nothing that Git keeps.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { ESLint } from "eslint";

const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const eslint = new ESLint({ cwd: ROOT });

async function linted(path) {
  return !(await eslint.isPathIgnored(path));
}

test("ESLint skips the website, its cache, the virtual environments and the packages", async () => {
  for (const path of [
    // A local build of the website, with the scripts that its privacy plugin downloads.
    "site/assets/javascripts/bundle.js",
    ".cache/plugin/privacy/assets/external/unpkg.com/mermaid@11/dist/mermaid.min.js",
    // The tools of the preview, as CONTRIBUTING sets them up, on Linux and on Windows.
    ".venv-docs/lib/python3.14/site-packages/material/templates/assets/javascripts/bundle.js",
    ".venv-docs/Lib/site-packages/material/templates/assets/javascripts/bundle.js",
    ".venv/lib/python3.14/site-packages/homeassistant/components/frontend/x.js",
    "node_modules/eslint/lib/api.js",
    ".github/prose/node_modules/cspell/bin.mjs",
    "htmlcov/coverage_html.js",
  ]) {
    assert.equal(await linted(path), false, path);
  }
});

test("ESLint skips every folder that .gitignore ignores, at the top or anywhere", async () => {
  const folders = readFileSync(new URL("../../.gitignore", import.meta.url), "utf8")
    .split(/\r?\n/u)
    .map((line) => line.trim())
    .filter((line) => line.endsWith("/") && !line.startsWith("#") && !line.startsWith("!"));
  assert.ok(folders.includes("/.cache/") && folders.includes("/.venv-docs/"), folders.join(" "));
  for (const folder of folders) {
    const path = `${folder.replace(/^\//u, "")}scripts/x.js`;
    assert.equal(await linted(path), false, path);
    // A folder without a leading slash, such as __pycache__/, is ignored at every depth.
    if (!folder.startsWith("/")) {
      assert.equal(await linted(`custom_components/homedarts/${path}`), false, path);
    }
  }
});

test("ESLint lints every JavaScript file that Git keeps", async () => {
  const files = execFileSync("git", ["ls-files", "-z", "--", "*.js", "*.mjs", "*.cjs"], {
    cwd: ROOT,
    encoding: "utf8",
  })
    .split("\0")
    .filter(Boolean);
  assert.ok(files.includes("custom_components/homedarts/frontend/homedarts-card.js"));
  assert.ok(files.includes("eslint.config.mjs"));
  for (const file of files) {
    assert.equal(await linted(file), true, file);
  }
});
