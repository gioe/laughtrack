import {
    ADMIN_DELETE_ENTITY_TYPES,
    adminDeleteWorkflows,
    type AdminDeleteEntityType,
} from "@/lib/admin/deleteWorkflows";
import { writeAdminActionAudit } from "@/lib/admin/audit";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const entityTypeSchema = z.enum(ADMIN_DELETE_ENTITY_TYPES);

const dependencySchema = z
    .object({
        key: z.string().min(1),
        label: z.string().min(1),
        count: z.number().int().nonnegative(),
    })
    .strict();

const targetSchema = z
    .object({
        entityType: entityTypeSchema,
        entityId: z.number().int().positive(),
    })
    .strict();

const confirmationSchema = targetSchema
    .extend({
        label: z.string().min(1).max(500),
        dependencies: z.array(dependencySchema),
    })
    .strict();

const deleteSchema = targetSchema
    .extend({
        reason: z.string().trim().min(1).max(1000),
        confirmation: confirmationSchema,
    })
    .strict();

type DeleteTarget = z.infer<typeof targetSchema>;

async function readJson(req: NextRequest): Promise<
    | { ok: true; body: unknown }
    | { ok: false; response: NextResponse<{ error: string }> }
> {
    try {
        return { ok: true, body: await req.json() };
    } catch {
        return {
            ok: false,
            response: NextResponse.json(
                { error: "Body must be valid JSON" },
                { status: 400 },
            ),
        };
    }
}

function workflowFor(entityType: AdminDeleteEntityType) {
    return adminDeleteWorkflows[entityType];
}

function confirmationFor(preview: {
    entityType: AdminDeleteEntityType;
    entityId: number;
    label: string;
    dependencies: unknown;
}) {
    return {
        entityType: preview.entityType,
        entityId: preview.entityId,
        label: preview.label,
        dependencies: preview.dependencies,
    };
}

function invalidPayload(error: z.ZodError) {
    return NextResponse.json(
        { error: "Invalid payload", issues: error.issues },
        { status: 400 },
    );
}

async function loadPreview(target: DeleteTarget) {
    return db.$transaction((tx) =>
        workflowFor(target.entityType).preview(tx, target.entityId),
    );
}

export async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const json = await readJson(req);
    if (!json.ok) return json.response;

    const parsed = targetSchema.safeParse(json.body);
    if (!parsed.success) return invalidPayload(parsed.error);

    const preview = await loadPreview(parsed.data);
    if (!preview) {
        return NextResponse.json(
            { error: "Entity not found" },
            { status: 404 },
        );
    }

    return NextResponse.json({
        ok: true,
        preview: {
            entityType: preview.entityType,
            entityId: preview.entityId,
            label: preview.label,
            dependencies: preview.dependencies,
            confirmation: confirmationFor(preview),
        },
    });
}

export async function DELETE(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const json = await readJson(req);
    if (!json.ok) return json.response;

    const parsed = deleteSchema.safeParse(json.body);
    if (!parsed.success) return invalidPayload(parsed.error);

    const { entityType, entityId, reason, confirmation } = parsed.data;
    const workflow = workflowFor(entityType);

    try {
        const deleted = await db.$transaction(async (tx) => {
            const preview = await workflow.preview(tx, entityId);
            if (!preview) return null;

            const expectedConfirmation = confirmationFor(preview);
            if (
                confirmation.entityType !== expectedConfirmation.entityType ||
                confirmation.entityId !== expectedConfirmation.entityId ||
                confirmation.label !== expectedConfirmation.label ||
                JSON.stringify(confirmation.dependencies) !==
                    JSON.stringify(expectedConfirmation.dependencies)
            ) {
                return { mismatch: expectedConfirmation };
            }

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: `${entityType}.delete`,
                entityType,
                entityId,
                reason,
                before: {
                    entity: preview.before,
                    dependencies: preview.dependencies,
                },
                after: { deleted: true },
            });
            await workflow.delete(tx, entityId);

            return { preview };
        });

        if (!deleted) {
            return NextResponse.json(
                { error: "Entity not found" },
                { status: 404 },
            );
        }
        if ("mismatch" in deleted) {
            return NextResponse.json(
                {
                    error: "Confirmation does not match current entity",
                    expectedConfirmation: deleted.mismatch,
                },
                { status: 400 },
            );
        }

        for (const tag of workflow.revalidationTags(deleted.preview)) {
            revalidateTag(tag);
        }

        return NextResponse.json({
            ok: true,
            deleted: {
                entityType: deleted.preview.entityType,
                entityId: deleted.preview.entityId,
                label: deleted.preview.label,
                dependencies: deleted.preview.dependencies,
            },
        });
    } catch (error) {
        console.error("Admin delete failed:", error);
        return NextResponse.json({ error: "Delete failed" }, { status: 500 });
    }
}
