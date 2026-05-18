CREATE TABLE "admin_action_audits" (
    "id" SERIAL PRIMARY KEY,
    "actor_profile_id" TEXT REFERENCES "user_profiles"("id") ON DELETE SET NULL,
    "action" TEXT NOT NULL,
    "entity_type" TEXT NOT NULL,
    "entity_id" TEXT NOT NULL,
    "reason" TEXT,
    "before_json" JSONB NOT NULL DEFAULT '{}',
    "after_json" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX "admin_action_audits_actor_profile_id_idx"
    ON "admin_action_audits"("actor_profile_id");

CREATE INDEX "admin_action_audits_entity_type_entity_id_created_at_idx"
    ON "admin_action_audits"("entity_type", "entity_id", "created_at" DESC);

CREATE INDEX "admin_action_audits_action_created_at_idx"
    ON "admin_action_audits"("action", "created_at" DESC);

CREATE INDEX "admin_action_audits_created_at_idx"
    ON "admin_action_audits"("created_at" DESC);
