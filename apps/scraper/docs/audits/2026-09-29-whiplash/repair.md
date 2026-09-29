# Applied repair and rollback

Prisma migration 20260929150000_correct_whiplash_identity applied successfully on 2026-09-29. The deploy preflight confirmed it was the only pending migration. The post-deploy query confirmed the row actually changed; migration success alone was not treated as sufficient proof.

The repair changes nine identity/location fields on club1347. All other club fields, the complete source591 row, and every captured club/show foreign-key count and fingerprint remained identical between operation-before.json and after.json. This includes 26 shows, 48 tickets, 14 lineup entries, 56 show tags, three home-club references, 138 scraper-run references, 798 club-linked clicks and 619 show-linked clicks. There were no saved shows, favorites or notification references. Earlier discovery snapshots may differ because production remained active before the operation snapshot.

Before production application, the exact SQL and rollback were tested in an always-rolled-back production transaction: apply, exact replay, complete club restoration, rollback replay, identity/source/image drift rejection, and refusal to roll back over subsequent edits. See migration-validation.json.

rollback.sql is an operator-only recovery artifact. It intentionally restores the known-wrong Brooklyn identity, so use it only to reverse this specific migration after reviewing why rollback is necessary. It validates current identity and source ownership and refuses later changes. Execute it inside an explicit transaction, inspect the result, then commit only when rollback is actually intended. Running it does not remove the Prisma migration ledger entry.
