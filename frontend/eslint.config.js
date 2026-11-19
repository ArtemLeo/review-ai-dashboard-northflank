import pluginVue from "eslint-plugin-vue";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import parser from "@typescript-eslint/parser";
import prettier from "eslint-config-prettier";
import globals from "globals";

/**
 * Flat ESLint configuration for the project (ESLint 9).
 *
 * The TypeScript and Vue recommended rulesets, plus a few project specific
 * overrides.  Formatting is Prettier's job, so `eslint-config-prettier` comes
 * last and switches off every stylistic rule that would fight it.
 */
export default [
  { ignores: ["dist/**", "node_modules/**", "eslint.config.js"] },
  // TypeScript recommended rules (parser + plugin + rules).
  ...tsPlugin.configs["flat/recommended"],
  // Vue recommended rules (vue-eslint-parser + browser globals).
  ...pluginVue.configs["flat/recommended"],
  {
    files: ["src/**/*.ts", "src/**/*.d.ts"],
    languageOptions: {
      globals: { ...globals.browser },
    },
    rules: {
      // AGENTS.md forbids `any`, so the lint fails on it instead of warning.
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  {
    files: ["src/**/*.vue"],
    languageOptions: {
      // vue-eslint-parser delegates the TypeScript block to the TS parser.
      parserOptions: {
        parser: parser,
        ecmaVersion: "latest",
        sourceType: "module",
      },
      globals: { ...globals.browser },
    },
    rules: {
      "vue/multi-word-component-names": "off",
      "vue/no-unused-components": "error",
      "vue/no-template-key": "error",
      "vue/no-setup-props-reactivity-loss": "error",
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  prettier,
];
