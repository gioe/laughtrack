# Web Dependency Audit Notes

## 2026-05-07 audit triage

`npm audit --audit-level=high` passes after updating the web dependency graph.
The high-severity findings were resolved by moving Vitest to `4.1.5`, adding
Vite `7.3.2`, and refreshing affected transitive packages in `package-lock.json`.

Nodemailer was upgraded from `7.0.13` to `8.0.7` after reviewing the app's only
email-sending path, `auth.ts`, and the Nodemailer 8 release notes. The documented
breaking change is the error code rename from `NoAuth` to `ENOAUTH`; this app
does not inspect Nodemailer error codes directly, so no application code change
is needed for the upgrade.

The remaining moderate audit finding is `next`'s nested `postcss` dependency.
`npm audit fix --force` proposes installing `next@9.3.3`, which would be an
unsafe downgrade from the current Next 15 line. Leave this as a tracked upstream
framework advisory until a compatible Next release updates the nested dependency
or the advisory metadata stops flagging the pinned version.
