# Parent relationship curation

`alias_of` uses the shared curation relationship and immutable decision ledger.
Propose records both endpoints and evidence. Confirm establishes a parent; reject
retains a negative pair; sever removes a confirmed parent and retains that negative
pair. Restore returns a rejected/severed pair to proposed, never confirmed. Neither
endpoint is identity-approved, deleted or blocked by a relationship decision.

The parent editor requires a reason and, for establishment, an independent
same-performer source URL and explanation. Both endpoints must already have
approved, visible, validated identities; the target must be canonical and neither
name may be denied. An embedded name or automatic normalization is insufficient.
The history panel shows evidence and decisions and supports previewed rejection
and restoration. The unified inbox presentation is TASK-4185.

`POST /api/admin/curation/parents` supports propose, preview and submit; GET accepts
childId for history. The old set-parent route delegates to this service and now
requires reason, requestId and previewToken. Submit rechecks the preview under the
shared intake lock. Replacing a parent severs the previous edge and confirms the
new one in one transaction. The unique active-parent index, cycle guard and shared
lock cover competing writers; stale previews must be regenerated. Replays use the
original immutable request receipt.

The database projects confirmed relationships into parent_comedian_id, rejects
unreviewed direct parent writes, and bumps the public cache revision. Existing
canonical resolution and public grouping read that projection. Original lineup,
appearance, podcast attribution and favorite rows stay on their original identities;
no historical rows are transferred or erased. Rejection and severing remain scoped
to the pair across sources. Automatic alias scripts can only propose; the old
reconcile-deny-list resurrection path fails closed without changing records.

## Deployment preflight

This migration deliberately refuses legacy FK/ledger disagreement, in either
direction. Do not run migrate deploy until explicit legacy reconciliation is
complete; a preflight failure in Prisma would block later migrations. Preserve
lineage snapshots and imported observations. Review each existing assignment with
its identity evidence, actor and reason: retain valid relationships through explicit
confirmed ledger decisions, or record rejected/severed decisions and explicitly
clear the obsolete FK with its historical effects reviewed. Do this reconciliation
before installing the new projection guard; do not auto-confirm all legacy links.
The existing curation migration planner imports legacy assignments as proposals,
not approval. Pending identity records must be reviewed independently.

Read-only checks (both must return zero before deployment):

```sql
SELECT count(*) FROM comedians c
WHERE c.parent_comedian_id IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM curation_relationships r
 JOIN curation_entities s ON s.id=r.source_id
 JOIN curation_entities t ON t.id=r.target_id
 WHERE r.kind='alias_of' AND r.disposition='confirmed'
 AND s.comedian_id=c.id AND t.comedian_id=c.parent_comedian_id
);
SELECT count(*) FROM curation_relationships r
JOIN curation_entities s ON s.id=r.source_id
JOIN curation_entities t ON t.id=r.target_id
LEFT JOIN comedians c ON c.id=s.comedian_id
WHERE r.kind='alias_of' AND r.disposition='confirmed'
AND (s.comedian_id IS NULL OR t.comedian_id IS NULL
 OR c.parent_comedian_id IS DISTINCT FROM t.comedian_id);
```

The 2026-10-16 read-only production inventory contained 490 parent assignments,
with no self-links. No production records or migrations were changed by this task.
Production also has the earlier failed club-intake migration; follow the recovery
instructions in CURATION-SHOW-INTAKE.md before any schema rollout.

Validation can use a read-only snapshot of id/name/parent_comedian_id/parent_name:
`CURATION_PARENT_SNAPSHOT=/private/tmp/snapshot.json npm test -- lib/admin/curation/parentRelationships.test.ts`.
The test first proves unreconciled links refuse installation, simulates review only
inside a disposable database, then verifies the reconciled projection is preserved.
It does not approve snapshot records in production. CI uses a small synthetic pair.
