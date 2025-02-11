/*
  Warnings:

  - The primary key for the `favorite_comedians` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - The primary key for the `tags` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - You are about to drop the `users` table. If the table is not empty, all the data it contains will be lost.
  - A unique constraint covering the columns `[id]` on the table `tags` will be added. If there are existing duplicate values, this will fail.
  - Made the column `type` on table `tags` required. This step will fail if there are existing NULL values in that column.
  - Made the column `value` on table `tags` required. This step will fail if there are existing NULL values in that column.

*/
-- DropForeignKey
ALTER TABLE "favorite_comedians" DROP CONSTRAINT "favorite_comedians_user_id_fkey";

-- AlterTable
ALTER TABLE "favorite_comedians" DROP CONSTRAINT "favorite_comedians_pkey",
ALTER COLUMN "user_id" SET DATA TYPE TEXT,
ADD CONSTRAINT "favorite_comedians_pkey" PRIMARY KEY ("user_id", "comedian_id");

ALTER TABLE "tagged_clubs" DROP CONSTRAINT IF EXISTS "tagged_clubs_tag_id_fkey";
ALTER TABLE "tagged_comedians" DROP CONSTRAINT IF EXISTS "tagged_comedians_tag_id_fkey";
ALTER TABLE "tagged_shows" DROP CONSTRAINT IF EXISTS "tagged_shows_tag_id_fkey";

-- Optional: Drop the columns if you don't need them anymore
ALTER TABLE "tagged_clubs" DROP COLUMN IF EXISTS "tag_id";
ALTER TABLE "tagged_comedians" DROP COLUMN IF EXISTS "tag_id";
ALTER TABLE "tagged_shows" DROP COLUMN IF EXISTS "tag_id";

-- AlterTable
ALTER TABLE "tags" DROP CONSTRAINT "tags_pkey",
ALTER COLUMN "type" SET NOT NULL,
ALTER COLUMN "value" SET NOT NULL,
ADD CONSTRAINT "tags_pkey" PRIMARY KEY ("type", "value");

-- DropTable
DROP TABLE "users";

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "name" TEXT,
    "email" TEXT NOT NULL,
    "emailVerified" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "UserProfile" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "role" TEXT NOT NULL DEFAULT 'user',
    "email_show_notifications" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "UserProfile_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Account" (
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

    CONSTRAINT "Account_pkey" PRIMARY KEY ("provider","providerAccountId")
);

-- CreateTable
CREATE TABLE "Session" (
    "sessionToken" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "expires" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL
);

-- CreateTable
CREATE TABLE "VerificationToken" (
    "identifier" TEXT NOT NULL,
    "token" TEXT NOT NULL,
    "expires" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "VerificationToken_pkey" PRIMARY KEY ("identifier","token")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "UserProfile_userId_key" ON "UserProfile"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "Session_sessionToken_key" ON "Session"("sessionToken");

-- CreateIndex
CREATE UNIQUE INDEX "tags_id_key" ON "tags"("id");

-- AddForeignKey
ALTER TABLE "UserProfile" ADD CONSTRAINT "UserProfile_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Account" ADD CONSTRAINT "Account_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Session" ADD CONSTRAINT "Session_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "favorite_comedians" ADD CONSTRAINT "favorite_comedians_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
