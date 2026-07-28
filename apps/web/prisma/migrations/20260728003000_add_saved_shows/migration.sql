-- CreateTable
CREATE TABLE "saved_shows" (
    "profile_id" TEXT NOT NULL,
    "show_id" INTEGER NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "saved_shows_pkey" PRIMARY KEY ("profile_id", "show_id")
);

-- CreateIndex
CREATE INDEX "saved_shows_show_id_idx" ON "saved_shows"("show_id");

-- AddForeignKey
ALTER TABLE "saved_shows" ADD CONSTRAINT "saved_shows_profile_id_fkey" FOREIGN KEY ("profile_id") REFERENCES "user_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "saved_shows" ADD CONSTRAINT "saved_shows_show_id_fkey" FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE CASCADE ON UPDATE CASCADE;
