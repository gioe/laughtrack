-- AlterTable: add notification_type column with default 'email'
ALTER TABLE "sent_notifications" ADD COLUMN "notification_type" TEXT NOT NULL DEFAULT 'email';

-- DropIndex: remove old unique constraint (userId, comedianId, showId)
DROP INDEX "sent_notifications_user_id_comedian_id_show_id_key";

-- CreateIndex: new unique constraint including notification_type
CREATE UNIQUE INDEX "sent_notifications_unique_per_channel" ON "sent_notifications"("user_id", "comedian_id", "show_id", "notification_type");
