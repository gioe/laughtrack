-- CreateTable
CREATE TABLE "email_subscriptions" (
    "id" SERIAL NOT NULL,
    "club_id" INTEGER NOT NULL,
    "sender_domain" TEXT NOT NULL,
    "subscribed" BOOLEAN NOT NULL DEFAULT true,
    "last_received" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "email_subscriptions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "processed_emails" (
    "id" SERIAL NOT NULL,
    "message_id" TEXT NOT NULL,
    "club_id" INTEGER NOT NULL,
    "received_at" TIMESTAMP(3) NOT NULL,
    "processed_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "processed_emails_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "email_subscriptions_club_id_key" ON "email_subscriptions"("club_id");

-- CreateIndex
CREATE UNIQUE INDEX "processed_emails_message_id_key" ON "processed_emails"("message_id");

-- AddForeignKey
ALTER TABLE "email_subscriptions" ADD CONSTRAINT "email_subscriptions_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "processed_emails" ADD CONSTRAINT "processed_emails_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE;
