# Tusk Task Checks

API and frontend task checks run the web Vitest suite followed by
`npm run type-check`. DTO and schema changes can satisfy focused tests while
still breaking TypeScript contracts used by Server Components, Client
Components, or shared route types, so the task-level domain gate must include
the web type-check before commit or merge.
