import { Prisma } from "@prisma/client";

type AdminActionAuditWriter = Pick<
    Prisma.TransactionClient,
    "adminActionAudit"
>;

export type AdminActionAuditInput = {
    actorProfileId: string | null;
    action: string;
    entityType: string;
    entityId: number | string;
    reason?: string | null;
    before: Prisma.InputJsonValue;
    after: Prisma.InputJsonValue;
};

export async function writeAdminActionAudit(
    tx: AdminActionAuditWriter,
    input: AdminActionAuditInput,
) {
    return tx.adminActionAudit.create({
        data: {
            actorProfileId: input.actorProfileId,
            action: input.action,
            entityType: input.entityType,
            entityId: String(input.entityId),
            reason: input.reason ?? null,
            before: input.before,
            after: input.after,
        },
    });
}
