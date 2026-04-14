-- CreateTable
CREATE TABLE "chains" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "website" TEXT,

    CONSTRAINT "chains_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "chains_name_key" ON "chains"("name");

-- CreateIndex
CREATE UNIQUE INDEX "chains_slug_key" ON "chains"("slug");

-- AlterTable
ALTER TABLE "clubs" ADD COLUMN "chain_id" INTEGER;

-- CreateIndex
CREATE INDEX "clubs_chain_id_idx" ON "clubs"("chain_id");

-- AddForeignKey
ALTER TABLE "clubs" ADD CONSTRAINT "clubs_chain_id_fkey" FOREIGN KEY ("chain_id") REFERENCES "chains"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- InsertChains
INSERT INTO "chains" ("name", "slug", "website") VALUES
    ('Improv', 'improv', 'https://improv.com'),
    ('Helium', 'helium', 'https://heliumcomedy.com'),
    ('Funny Bone', 'funny-bone', 'https://funnybone.com'),
    ('Comedy Zone', 'comedy-zone', NULL),
    ('Stress Factory', 'stress-factory', 'https://stressfactory.com'),
    ('Punch Line', 'punch-line', NULL),
    ('Laugh Factory', 'laugh-factory', 'https://laughfactory.com'),
    ('The Setup', 'the-setup', 'https://setupcomedy.com'),
    ('Zanies', 'zanies', 'https://zanies.com'),
    ('Wiseguys', 'wiseguys', 'https://wiseguyscomedy.com');

-- BackfillChainId: Improv (21 clubs — excludes DC Improv id=102, Improv Asylum, ImprovCity, Logan Square Improv, Philly Improv Theater, Stevie Ray's Improv)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'improv')
WHERE "id" IN (29, 39, 30, 31, 56, 104, 53, 460, 32, 40, 33, 41, 55, 34, 196, 35, 379, 36, 37, 38, 54);

-- BackfillChainId: Helium (6 clubs)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'helium')
WHERE "id" IN (132, 108, 110, 134, 139, 133);

-- BackfillChainId: Funny Bone (11 clubs — excludes duplicate Funny Bone Columbus id=1037 with no website)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'funny-bone')
WHERE "id" IN (323, 1050, 317, 1030, 308, 1026, 1027, 1034, 1028, 1053, 1033);

-- BackfillChainId: Comedy Zone (8 clubs)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'comedy-zone')
WHERE "id" IN (59, 492, 488, 638, 58, 60, 57, 73);

-- BackfillChainId: Stress Factory (4 clubs)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'stress-factory')
WHERE "id" IN (45, 130, 623, 46);

-- BackfillChainId: Punch Line (5 clubs)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'punch-line')
WHERE "id" IN (194, 198, 1044, 152, 1039);

-- BackfillChainId: Laugh Factory (7 clubs)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'laugh-factory')
WHERE "id" IN (168, 171, 160, 172, 169, 173, 170);

-- BackfillChainId: The Setup (5 clubs)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'the-setup')
WHERE "id" IN (660, 658, 195, 659, 661);

-- BackfillChainId: Zanies (2 clubs)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'zanies')
WHERE "id" IN (179, 1029);

-- BackfillChainId: Wiseguys (8 clubs)
UPDATE "clubs" SET "chain_id" = (SELECT "id" FROM "chains" WHERE "slug" = 'wiseguys')
WHERE "id" IN (404, 605, 390, 391, 389, 546, 586, 448);
