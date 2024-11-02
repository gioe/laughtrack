// @ts-check

import tseslint from "typescript-eslint";
import eslintConfigPrettier from "eslint-config-prettier";

export default [
  ...tseslint.configs.strict,
  ...tseslint.configs.stylistic,
  eslintConfigPrettier
];
