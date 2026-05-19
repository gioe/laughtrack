-- CreateTable
CREATE TABLE "favorite_podcasts" (
    "id" SERIAL NOT NULL,
    "podcast_id" INTEGER NOT NULL,
    "profile_id" TEXT NOT NULL,

    CONSTRAINT "favorite_podcasts_pkey" PRIMARY KEY ("profile_id","podcast_id")
);

-- CreateIndex
CREATE INDEX "favorite_podcasts_podcast_id_idx" ON "favorite_podcasts"("podcast_id");

-- AddForeignKey
ALTER TABLE "favorite_podcasts" ADD CONSTRAINT "favorite_podcasts_podcast_id_fkey" FOREIGN KEY ("podcast_id") REFERENCES "podcasts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorite_podcasts" ADD CONSTRAINT "favorite_podcasts_profile_id_fkey" FOREIGN KEY ("profile_id") REFERENCES "user_profiles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
