CREATE TABLE "user_push_tokens" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "profile_id" TEXT NOT NULL,
    "platform" TEXT NOT NULL DEFAULT 'ios',
    "token" TEXT NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "revoked_at" TIMESTAMPTZ,
    "last_registered_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_push_tokens_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "user_push_tokens_token_key" ON "user_push_tokens"("token");
CREATE INDEX "user_push_tokens_user_id_is_active_idx" ON "user_push_tokens"("user_id", "is_active");
CREATE INDEX "user_push_tokens_profile_id_is_active_idx" ON "user_push_tokens"("profile_id", "is_active");
CREATE INDEX "user_push_tokens_platform_is_active_idx" ON "user_push_tokens"("platform", "is_active");

ALTER TABLE "user_push_tokens"
  ADD CONSTRAINT "user_push_tokens_user_id_fkey"
  FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "user_push_tokens"
  ADD CONSTRAINT "user_push_tokens_profile_id_fkey"
  FOREIGN KEY ("profile_id") REFERENCES "user_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;
