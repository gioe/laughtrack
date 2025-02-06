-- AlterTable
ALTER TABLE "comedians" ADD COLUMN     "parent_comedian_id" INTEGER;

-- AddForeignKey
ALTER TABLE "comedians" ADD CONSTRAINT "comedians_parent_comedian_id_fkey" FOREIGN KEY ("parent_comedian_id") REFERENCES "comedians"("id") ON DELETE SET NULL ON UPDATE CASCADE;
