-- CreateTable
CREATE TABLE "clubs" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "address" TEXT NOT NULL,
    "website" TEXT NOT NULL,
    "scraping_url" TEXT NOT NULL,
    "popularity" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "zip_code" VARCHAR(10),
    "phone_number" TEXT DEFAULT '',
    "timezone" TEXT,
    "visible" BOOLEAN DEFAULT true,
    "scraper" TEXT,

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
    "total_shows" INTEGER NOT NULL DEFAULT 0,
    "sold_out_shows" INTEGER NOT NULL DEFAULT 0,
    "linktree" TEXT,
    "parent_comedian_id" INTEGER,

    CONSTRAINT "comedians_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "name" TEXT,
    "email" TEXT NOT NULL,
    "emailVerified" TIMESTAMP(3),
    "image" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_profiles" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "role" TEXT NOT NULL DEFAULT 'user',
    "email_show_notifications" BOOLEAN NOT NULL DEFAULT false,
    "zip_code" TEXT,

    CONSTRAINT "user_profiles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "accounts" (
    "userId" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "providerAccountId" TEXT NOT NULL,
    "refresh_token" TEXT,
    "access_token" TEXT,
    "expires_at" INTEGER,
    "token_type" TEXT,
    "scope" TEXT,
    "id_token" TEXT,
    "session_state" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "accounts_pkey" PRIMARY KEY ("provider","providerAccountId")
);

-- CreateTable
CREATE TABLE "sessions" (
    "sessionToken" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "expires" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL
);

-- CreateTable
CREATE TABLE "tokens" (
    "identifier" TEXT NOT NULL,
    "token" TEXT NOT NULL,
    "expires" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "tokens_pkey" PRIMARY KEY ("identifier","token")
);

-- CreateTable
CREATE TABLE "favorite_comedians" (
    "id" SERIAL NOT NULL,
    "comedian_id" TEXT NOT NULL,
    "profile_id" TEXT NOT NULL,

    CONSTRAINT "favorite_comedians_pkey" PRIMARY KEY ("profile_id","comedian_id")
);

-- CreateTable
CREATE TABLE "shows" (
    "id" SERIAL NOT NULL,
    "name" TEXT,
    "date" TIMESTAMPTZ(6) NOT NULL,
    "show_page_url" TEXT NOT NULL,
    "club_id" INTEGER NOT NULL,
    "popularity" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "last_scraped_date" TIMESTAMPTZ(6),
    "description" TEXT,

    CONSTRAINT "shows_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tickets" (
    "id" SERIAL NOT NULL,
    "purchase_url" TEXT,
    "price" DECIMAL(5,2),
    "sold_out" BOOLEAN NOT NULL DEFAULT false,
    "show_id" INTEGER NOT NULL,
    "type" TEXT,

    CONSTRAINT "tickets_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "lineup_items" (
    "id" SERIAL NOT NULL,
    "show_id" INTEGER NOT NULL,
    "comedian_id" TEXT NOT NULL,

    CONSTRAINT "lineup_items_pkey" PRIMARY KEY ("show_id","comedian_id")
);

-- CreateTable
CREATE TABLE "tags" (
    "id" SERIAL NOT NULL,
    "display" TEXT,
    "type" TEXT NOT NULL,
    "user_facing" BOOLEAN NOT NULL DEFAULT false,
    "value" TEXT NOT NULL,

    CONSTRAINT "tags_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tagged_clubs" (
    "id" SERIAL NOT NULL,
    "club_id" INTEGER NOT NULL,
    "tag_id" INTEGER NOT NULL,

    CONSTRAINT "tagged_clubs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tagged_comedians" (
    "id" SERIAL NOT NULL,
    "comedian_id" TEXT NOT NULL,
    "tag_id" INTEGER NOT NULL,

    CONSTRAINT "tagged_comedians_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tagged_shows" (
    "id" SERIAL NOT NULL,
    "show_id" INTEGER NOT NULL,
    "tag_id" INTEGER NOT NULL,

    CONSTRAINT "tagged_shows_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "clubs_name_key" ON "clubs"("name");

-- CreateIndex
CREATE UNIQUE INDEX "comedians_name_key" ON "comedians"("name");

-- CreateIndex
CREATE UNIQUE INDEX "comedians_uuid_key" ON "comedians"("uuid");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "user_profiles_userId_key" ON "user_profiles"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "sessions_sessionToken_key" ON "sessions"("sessionToken");

-- CreateIndex
CREATE UNIQUE INDEX "shows_club_id_date_key" ON "shows"("club_id", "date");

-- CreateIndex
CREATE UNIQUE INDEX "tickets_show_id_type_key" ON "tickets"("show_id", "type");

-- CreateIndex
CREATE UNIQUE INDEX "tags_type_value_key" ON "tags"("type", "value");

-- CreateIndex
CREATE UNIQUE INDEX "tagged_comedians_comedian_id_tag_id_key" ON "tagged_comedians"("comedian_id", "tag_id");

-- CreateIndex
CREATE UNIQUE INDEX "tagged_shows_show_id_tag_id_key" ON "tagged_shows"("show_id", "tag_id");

-- AddForeignKey
ALTER TABLE "comedians" ADD CONSTRAINT "comedians_parent_comedian_id_fkey" FOREIGN KEY ("parent_comedian_id") REFERENCES "comedians"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_profiles" ADD CONSTRAINT "user_profiles_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "accounts" ADD CONSTRAINT "accounts_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorite_comedians" ADD CONSTRAINT "favorite_comedians_comedian_id_fkey" FOREIGN KEY ("comedian_id") REFERENCES "comedians"("uuid") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorite_comedians" ADD CONSTRAINT "favorite_comedians_profile_id_fkey" FOREIGN KEY ("profile_id") REFERENCES "user_profiles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "shows" ADD CONSTRAINT "shows_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tickets" ADD CONSTRAINT "tickets_show_id_fkey" FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lineup_items" ADD CONSTRAINT "lineup_items_comedian_id_fkey" FOREIGN KEY ("comedian_id") REFERENCES "comedians"("uuid") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lineup_items" ADD CONSTRAINT "lineup_items_show_id_fkey" FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_clubs" ADD CONSTRAINT "tagged_clubs_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_clubs" ADD CONSTRAINT "tagged_clubs_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_comedians" ADD CONSTRAINT "tagged_comedians_comedian_id_fkey" FOREIGN KEY ("comedian_id") REFERENCES "comedians"("uuid") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_comedians" ADD CONSTRAINT "tagged_comedians_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_shows" ADD CONSTRAINT "tagged_shows_show_id_fkey" FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_shows" ADD CONSTRAINT "tagged_shows_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
