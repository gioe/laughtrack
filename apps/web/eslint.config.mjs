import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import nextPlugin from "@next/eslint-plugin-next";

export default [
  { ignores: ["node_modules/**", ".next/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  // Use the full v7 recommended-latest flat config (enables static-components,
  // use-memo, immutability, refs, purity, error-boundaries, etc.).
  reactHooks.configs.flat["recommended-latest"],
  {
    plugins: { "@next/next": nextPlugin },
    rules: {
      ...nextPlugin.configs.recommended.rules,
    },
  },
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "warn",
      // Disable React Compiler-specific rules — these flag legitimate standard
      // React patterns (setState in effects, manual useMemo) that are correct
      // and intentional in codebases that do not use the React Compiler.
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/preserve-manual-memoization": "off",
    },
  },
];
