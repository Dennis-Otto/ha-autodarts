// The rules of the JavaScript of this repository: ESLint's recommended rules, for the
// dashboard cards in the browser and for their tests and the scripts in Node.
// https://eslint.org/docs/latest/use/configure/
import { fileURLToPath } from "node:url";
import js from "@eslint/js";
import { includeIgnoreFile } from "eslint/config";
import globals from "globals";

export default [
  // What Git ignores, ESLint skips too: the packages of npm, the virtual environments,
  // the website that MkDocs builds and its cache, the coverage report and the
  // artifacts of the tests, whose JavaScript is not ours. A folder that .gitignore
  // gains is skipped without a change here (tests/frontend/eslint-config.test.mjs).
  // https://eslint.org/docs/latest/use/configure/ignore#including-gitignore-files
  includeIgnoreFile(fileURLToPath(new URL(".gitignore", import.meta.url)), "What Git ignores"),
  js.configs.recommended,
  {
    rules: {
      // A name that starts with _ is unused on purpose, and so is what a rest
      // pattern leaves out of an object.
      "no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", ignoreRestSiblings: true },
      ],
    },
  },
  {
    files: ["custom_components/homedarts/frontend/**/*.js", "docs/demo/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
    },
  },
  // The scripts that the blueprint keeps current in .github/: the one of the website,
  // which the browser runs as a classic script, and the accessibility check of the
  // website in Node, which runs parts of itself in the pages that it opens.
  {
    files: [".github/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: globals.browser,
    },
  },
  {
    files: [".github/**/*.mjs"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.node, ...globals.browser },
    },
  },
  {
    files: ["tests/**/*.js", "tests/**/*.mjs", "scripts/**/*.mjs", "eslint.config.mjs"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.node, ...globals.browser },
    },
  },
];
