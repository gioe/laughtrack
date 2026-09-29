# Guarded production repair

Applied only migration20260929190000_quarantine_laugh_tonight_identity with the
locally pinned Prisma CLI on 2026-09-29. The pending-migration preflight required
this to be the sole pending migration and rejected any unresolved failed entry.

Club855 is hidden, typed producer, has_image=false, website normalized to HTTPS,
and its stale description replaced. Foreign street/city/state/Google place and
coordinates are cleared. Blank ZIP remains blank; no new physical address is
claimed. Account timezone and all historical show timestamps remain unchanged.
Source294 remains owned by855 with SeatEngine424 and its original URL/config;
enabled=false and task_4070_disposition contains original field/source images.
Existing TASK-1984 canonical metadata is preserved. No place is deny-listed.

validation.json records rollback-only production trials: forward change, repeat
application, inverse and repeated inverse; changed identity, typed source ID,
metadata, later location edits and intervening source enable all fail closed.
Both directions lock clubs/sources during the transition. Source updated_at is
trigger-maintained and deliberately excluded from equality checks; all other
source fields restore exactly. rollback.sql restores the known-bad original
identity/visibility, so it is an operator recovery artifact, not a scheduled job.

The immediate operation-before/after snapshots prove all historical reference
counts and fingerprints are unchanged. Three shows, eight tickets, six lineup
links, six show tags,25 clicks,138 run links and one home-comedian link remain.
Only the source fingerprint changes, reflecting its reviewed disable/metadata.
The post-apply source count remains one and no upcoming show existed at apply.
