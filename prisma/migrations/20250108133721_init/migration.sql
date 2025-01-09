-- CreateTable
CREATE TABLE "cities" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,

    CONSTRAINT "cities_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "clubs" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "address" TEXT NOT NULL,
    "website" TEXT NOT NULL,
    "scraping_url" TEXT NOT NULL,
    "popularity" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "zip_code" VARCHAR(10),
    "city_id" INTEGER NOT NULL,
    "scraper_type" TEXT,

    CONSTRAINT "clubs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "comedians" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "instagram_account" TEXT,
    "instagram_followers" INTEGER,
    "tiktok_account" TEXT,
    "tiktok_followers" INTEGER,
    "website" TEXT,
    "popularity" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "youtube_account" TEXT,
    "youtube_followers" INTEGER,
    "uuid" TEXT NOT NULL,
    "linktree" TEXT,

    CONSTRAINT "comedians_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" SERIAL NOT NULL,
    "email" TEXT NOT NULL,
    "password" TEXT NOT NULL,
    "role" TEXT NOT NULL DEFAULT 'user',
    "zip_code" VARCHAR(10),

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "favorite_comedians" (
    "id" SERIAL NOT NULL,
    "comedian_id" TEXT NOT NULL,
    "user_id" INTEGER NOT NULL,

    CONSTRAINT "favorite_comedians_pkey" PRIMARY KEY ("user_id","comedian_id")
);

-- CreateTable
CREATE TABLE "shows" (
    "id" SERIAL NOT NULL,
    "name" TEXT,
    "date" TIMESTAMP(3) NOT NULL,
    "show_page_url" TEXT NOT NULL,
    "club_id" INTEGER NOT NULL,
    "ticket_price_currency" TEXT NOT NULL DEFAULT 'USD',
    "popularity" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "last_scraped_date" TIMESTAMP(3),
    "description" TEXT,
    "ticket_purchase_url" TEXT,
    "ticket_price" DECIMAL(5,2),
    "supplied_tags" TEXT[],

    CONSTRAINT "shows_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "lineup_items" (
    "id" SERIAL NOT NULL,
    "show_id" INTEGER NOT NULL,
    "comedian_id" TEXT NOT NULL,

    CONSTRAINT "lineup_items_pkey" PRIMARY KEY ("show_id","comedian_id")
);

-- CreateTable
CREATE TABLE "tag_category" (
    "id" SERIAL NOT NULL,
    "display" TEXT,
    "type" TEXT,
    "value" TEXT,

    CONSTRAINT "tag_category_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tags" (
    "id" SERIAL NOT NULL,
    "display" TEXT,
    "type" TEXT,
    "user_facing" BOOLEAN NOT NULL DEFAULT false,
    "pattern" TEXT,
    "category" INTEGER,
    "value" TEXT,
    "key_words" TEXT[],

    CONSTRAINT "tags_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tagged_clubs" (
    "id" SERIAL NOT NULL,
    "club_id" INTEGER NOT NULL,
    "tag_id" INTEGER NOT NULL,

    CONSTRAINT "tagged_clubs_pkey" PRIMARY KEY ("club_id","tag_id")
);

-- CreateTable
CREATE TABLE "tagged_comedians" (
    "id" SERIAL NOT NULL,
    "comedian_id" TEXT NOT NULL,
    "tag_id" INTEGER NOT NULL,

    CONSTRAINT "tagged_comedians_pkey" PRIMARY KEY ("comedian_id","tag_id")
);

-- CreateTable
CREATE TABLE "tagged_shows" (
    "id" SERIAL NOT NULL,
    "show_id" INTEGER NOT NULL,
    "tag_id" INTEGER NOT NULL,

    CONSTRAINT "tagged_shows_pkey" PRIMARY KEY ("show_id","tag_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "cities_name_key" ON "cities"("name");

-- CreateIndex
CREATE UNIQUE INDEX "clubs_name_key" ON "clubs"("name");

-- CreateIndex
CREATE UNIQUE INDEX "comedians_name_key" ON "comedians"("name");

-- CreateIndex
CREATE UNIQUE INDEX "comedians_uuid_key" ON "comedians"("uuid");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "shows_club_id_date_key" ON "shows"("club_id", "date");

-- AddForeignKey
ALTER TABLE "clubs" ADD CONSTRAINT "clubs_city_id_fkey" FOREIGN KEY ("city_id") REFERENCES "cities"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorite_comedians" ADD CONSTRAINT "favorite_comedians_comedian_id_fkey" FOREIGN KEY ("comedian_id") REFERENCES "comedians"("uuid") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorite_comedians" ADD CONSTRAINT "favorite_comedians_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "shows" ADD CONSTRAINT "shows_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lineup_items" ADD CONSTRAINT "lineup_items_show_id_fkey" FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lineup_items" ADD CONSTRAINT "lineup_items_comedian_id_fkey" FOREIGN KEY ("comedian_id") REFERENCES "comedians"("uuid") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tags" ADD CONSTRAINT "tags_category_fkey" FOREIGN KEY ("category") REFERENCES "tag_category"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_clubs" ADD CONSTRAINT "tagged_clubs_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_clubs" ADD CONSTRAINT "tagged_clubs_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_comedians" ADD CONSTRAINT "tagged_comedians_comedian_id_fkey" FOREIGN KEY ("comedian_id") REFERENCES "comedians"("uuid") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_comedians" ADD CONSTRAINT "tagged_comedians_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_shows" ADD CONSTRAINT "tagged_shows_show_id_fkey" FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_shows" ADD CONSTRAINT "tagged_shows_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE CASCADE ON UPDATE CASCADE;
