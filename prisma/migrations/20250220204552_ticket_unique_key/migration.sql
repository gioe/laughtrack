/*
  Warnings:

  - A unique constraint covering the columns `[show_id,purchase_url,type]` on the table `tickets` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "tickets_show_id_purchase_url_type_key" ON "tickets"("show_id", "purchase_url", "type");
