// The rules of the JavaScript of this repository: ESLint's recommended rules, for the
// dashboard cards in the browser and for their tests and the scripts in Node.
// https://eslint.org/docs/latest/use/configure/
import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["node_modules/", "htmlcov/", ".venv/", "site/"] },
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
    files: ["custom_components/autodarts/frontend/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
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
