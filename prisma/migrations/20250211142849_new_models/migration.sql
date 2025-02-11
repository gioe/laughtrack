/*
  Warnings:

  - You are about to drop the column `city_id` on the `clubs` table. All the data in the column will be lost.
  - The primary key for the `favorite_comedians` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - You are about to drop the column `user_id` on the `favorite_comedians` table. All the data in the column will be lost.
  - You are about to drop the column `sold_out` on the `shows` table. All the data in the column will be lost.
  - You are about to drop the column `ticket_price` on the `shows` table. All the data in the column will be lost.
  - You are about to drop the column `ticket_price_currency` on the `shows` table. All the data in the column will be lost.
  - You are about to drop the column `ticket_purchase_url` on the `shows` table. All the data in the column will be lost.
  - The primary key for the `tags` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - You are about to drop the `Account` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Session` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `User` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `UserProfile` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `VerificationToken` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `cities` table. If the table is not empty, all the data it contains will be lost.
  - A unique constraint covering the columns `[type,value]` on the table `tags` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `profile_id` to the `favorite_comedians` table without a default value. This is not possible if the table is not empty.
  - Added the required column `tag_id` to the `tagged_clubs` table without a default value. This is not possible if the table is not empty.
  - Added the required column `tag_id` to the `tagged_comedians` table without a default value. This is not possible if the table is not empty.
  - Added the required column `tag_id` to the `tagged_shows` table without a default value. This is not possible if the table is not empty.

*/
-- DropForeignKey
ALTER TABLE "Account" DROP CONSTRAINT "Account_userId_fkey";

-- DropForeignKey
ALTER TABLE "Session" DROP CONSTRAINT "Session_userId_fkey";

-- DropForeignKey
ALTER TABLE "UserProfile" DROP CONSTRAINT "UserProfile_userId_fkey";

-- DropForeignKey
ALTER TABLE "clubs" DROP CONSTRAINT "clubs_city_id_fkey";

-- DropForeignKey
ALTER TABLE "favorite_comedians" DROP CONSTRAINT "favorite_comedians_user_id_fkey";

-- DropIndex
DROP INDEX "tags_id_key";

-- AlterTable
ALTER TABLE "clubs" DROP COLUMN "city_id";

-- AlterTable
ALTER TABLE "comedians" ADD COLUMN     "sold_out_shows" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "total_shows" INTEGER NOT NULL DEFAULT 0;

-- AlterTable
ALTER TABLE "favorite_comedians" DROP CONSTRAINT "favorite_comedians_pkey",
DROP COLUMN "user_id",
ADD COLUMN     "profile_id" TEXT NOT NULL,
ADD CONSTRAINT "favorite_comedians_pkey" PRIMARY KEY ("profile_id", "comedian_id");

-- AlterTable
ALTER TABLE "shows" DROP COLUMN "sold_out",
DROP COLUMN "ticket_price",
DROP COLUMN "ticket_price_currency",
DROP COLUMN "ticket_purchase_url";

-- AlterTable
ALTER TABLE "tagged_clubs" ADD COLUMN     "tag_id" INTEGER NOT NULL,
ADD CONSTRAINT "tagged_clubs_pkey" PRIMARY KEY ("id");

-- DropIndex
DROP INDEX "tagged_clubs_id_key";

-- AlterTable
ALTER TABLE "tagged_comedians" ADD COLUMN     "tag_id" INTEGER NOT NULL,
ADD CONSTRAINT "tagged_comedians_pkey" PRIMARY KEY ("id");

-- DropIndex
DROP INDEX "tagged_comedians_id_key";

-- AlterTable
ALTER TABLE "tagged_shows" ADD COLUMN     "tag_id" INTEGER NOT NULL,
ADD CONSTRAINT "tagged_shows_pkey" PRIMARY KEY ("id");

-- DropIndex
DROP INDEX "tagged_shows_id_key";

-- AlterTable
ALTER TABLE "tags" DROP CONSTRAINT "tags_pkey",
ADD CONSTRAINT "tags_pkey" PRIMARY KEY ("id");

-- DropTable
DROP TABLE "Account";

-- DropTable
DROP TABLE "Session";

-- DropTable
DROP TABLE "User";

-- DropTable
DROP TABLE "UserProfile";

-- DropTable
DROP TABLE "VerificationToken";

-- DropTable
DROP TABLE "cities";

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "name" TEXT,
    "email" TEXT NOT NULL,
    "emailVerified" TIMESTAMP(3),
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
CREATE TABLE "tickets" (
    "id" SERIAL NOT NULL,
    "purchase_url" TEXT,
    "price" DECIMAL(5,2),
    "sold_out" BOOLEAN NOT NULL DEFAULT false,
    "show_id" INTEGER NOT NULL,
    "ticket_type" TEXT,

    CONSTRAINT "tickets_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "user_profiles_userId_key" ON "user_profiles"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "sessions_sessionToken_key" ON "sessions"("sessionToken");

-- CreateIndex
CREATE UNIQUE INDEX "tags_type_value_key" ON "tags"("type", "value");

-- AddForeignKey
ALTER TABLE "user_profiles" ADD CONSTRAINT "user_profiles_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "accounts" ADD CONSTRAINT "accounts_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorite_comedians" ADD CONSTRAINT "favorite_comedians_profile_id_fkey" FOREIGN KEY ("profile_id") REFERENCES "user_profiles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tickets" ADD CONSTRAINT "tickets_show_id_fkey" FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_clubs" ADD CONSTRAINT "tagged_clubs_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_comedians" ADD CONSTRAINT "tagged_comedians_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tagged_shows" ADD CONSTRAINT "tagged_shows_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
