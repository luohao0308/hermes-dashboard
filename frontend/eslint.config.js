// @ts-check
import tsPlugin from 'typescript-eslint'

// Only lint .ts files (Vue files are type-checked by vue-tsc in the build step)
export default [
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**', '**/*.vue'],
  },
  {
    files: ['**/*.ts'],
    plugins: { ts: tsPlugin },
    languageOptions: {
      parser: tsPlugin.parser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: 'module',
      },
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      'no-unused-vars': 'warn',
      'no-console': 'warn',
    },
  },
]
