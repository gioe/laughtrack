-- CreateTable
CREATE TABLE "production_companies" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "website" TEXT,
    "scraping_url" TEXT,
    "visible" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "production_companies_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "production_company_venues" (
    "production_company_id" INTEGER NOT NULL,
    "club_id" INTEGER NOT NULL,

    CONSTRAINT "production_company_venues_pkey" PRIMARY KEY ("production_company_id","club_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "production_companies_name_key" ON "production_companies"("name");

-- CreateIndex
CREATE UNIQUE INDEX "production_companies_slug_key" ON "production_companies"("slug");

-- AlterTable
ALTER TABLE "shows" ADD COLUMN "production_company_id" INTEGER;

-- CreateIndex
CREATE INDEX "shows_production_company_id_idx" ON "shows"("production_company_id");

-- AddForeignKey
ALTER TABLE "production_company_venues" ADD CONSTRAINT "production_company_venues_production_company_id_fkey" FOREIGN KEY ("production_company_id") REFERENCES "production_companies"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "production_company_venues" ADD CONSTRAINT "production_company_venues_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "shows" ADD CONSTRAINT "shows_production_company_id_fkey" FOREIGN KEY ("production_company_id") REFERENCES "production_companies"("id") ON DELETE SET NULL ON UPDATE CASCADE;
