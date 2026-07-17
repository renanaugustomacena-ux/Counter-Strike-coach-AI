// 26-WEB-01 / TASKS#62 (owner decision 2026-07-17): one flat config for the
// three workspace apps — the per-app `lint` scripts resolve it by walking up
// from each package directory. Pinned deps live in the workspace root
// manifest; eslint 9 flat-config per the R6 decision.
import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["**/dist/**", "**/node_modules/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/src/**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.browser } },
  },
);
