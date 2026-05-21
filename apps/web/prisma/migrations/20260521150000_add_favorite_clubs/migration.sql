-- CreateTable
CREATE TABLE "favorite_clubs" (
    "id" SERIAL NOT NULL,
    "club_id" INTEGER NOT NULL,
    "profile_id" TEXT NOT NULL,

    CONSTRAINT "favorite_clubs_pkey" PRIMARY KEY ("profile_id","club_id")
);

-- CreateIndex
CREATE INDEX "favorite_clubs_club_id_idx" ON "favorite_clubs"("club_id");

-- AddForeignKey
ALTER TABLE "favorite_clubs" ADD CONSTRAINT "favorite_clubs_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorite_clubs" ADD CONSTRAINT "favorite_clubs_profile_id_fkey" FOREIGN KEY ("profile_id") REFERENCES "user_profiles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
