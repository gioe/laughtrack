-- AlterTable: add notification_type column with default 'email' and a check constraint for valid channels
ALTER TABLE "sent_notifications"
  ADD COLUMN "notification_type" TEXT NOT NULL DEFAULT 'email',
  ADD CONSTRAINT "sent_notifications_notification_type_check" CHECK ("notification_type" IN ('email', 'push'));

-- Replace old unique constraint with per-channel constraint atomically
BEGIN;
DROP INDEX "sent_notifications_user_id_comedian_id_show_id_key";
CREATE UNIQUE INDEX "sent_notifications_unique_per_channel" ON "sent_notifications"("user_id", "comedian_id", "show_id", "notification_type");
COMMIT;
