/*
  Warnings:

  - You are about to drop the column `userId` on the `user_profiles` table. All the data in the column will be lost.
  - You are about to drop the `sessions` table. If the table is not empty, all the data it contains will be lost.
  - A unique constraint covering the columns `[user_id]` on the table `user_profiles` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `user_id` to the `user_profiles` table without a default value. This is not possible if the table is not empty.

*/
-- DropForeignKey
ALTER TABLE "sessions" DROP CONSTRAINT "sessions_userId_fkey";

-- DropForeignKey
ALTER TABLE "user_profiles" DROP CONSTRAINT "user_profiles_userId_fkey";

-- DropIndex
DROP INDEX "user_profiles_userId_key";

-- AlterTable
ALTER TABLE "user_profiles" DROP COLUMN "userId",
ADD COLUMN     "user_id" TEXT NOT NULL;

-- DropTable
DROP TABLE "sessions";

-- CreateIndex
CREATE UNIQUE INDEX "user_profiles_user_id_key" ON "user_profiles"("user_id");

-- AddForeignKey
ALTER TABLE "user_profiles" ADD CONSTRAINT "user_profiles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
