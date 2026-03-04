-- CreateTable
CREATE TABLE "sent_notifications" (
    "id" SERIAL NOT NULL,
    "user_id" TEXT NOT NULL,
    "comedian_id" TEXT NOT NULL,
    "show_id" INTEGER NOT NULL,
    "sent_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "sent_notifications_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "sent_notifications_user_id_comedian_id_show_id_key" ON "sent_notifications"("user_id", "comedian_id", "show_id");

-- CreateIndex
CREATE INDEX "sent_notifications_user_id_idx" ON "sent_notifications"("user_id");

-- AddForeignKey
ALTER TABLE "sent_notifications" ADD CONSTRAINT "sent_notifications_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sent_notifications" ADD CONSTRAINT "sent_notifications_comedian_id_fkey" FOREIGN KEY ("comedian_id") REFERENCES "comedians"("uuid") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sent_notifications" ADD CONSTRAINT "sent_notifications_show_id_fkey" FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE CASCADE ON UPDATE CASCADE;
