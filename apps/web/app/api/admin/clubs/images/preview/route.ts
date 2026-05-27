import {
    ComedianImageDownloadError,
    HERO_HEIGHT,
    HERO_WIDTH,
    downloadComedianImage,
    generateClubImageVariants,
    readUploadedComedianImage,
    type DownloadedComedianImage,
} from "@/lib/admin/comedianImagePipeline";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z
    .object({
        clubId: z.number().int().positive(),
        iconImageUrl: z.string().url().max(2048).optional(),
        heroImageUrl: z.string().url().max(2048).optional(),
    })
    .strict();

type ImageSlot = "icon" | "hero";

type NormalizedRequest = {
    clubId: number;
    iconImageUrl?: string;
    heroImageUrl?: string;
    iconFile?: File;
    heroFile?: File;
};

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

function getOptionalFormString(formData: FormData, key: string) {
    const value = formData.get(key);
    return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function getOptionalFormFile(formData: FormData, key: string) {
    const value = formData.get(key);
    return value instanceof File && value.size > 0 ? value : undefined;
}

async function normalizeRequest(req: NextRequest) {
    const contentType = req.headers.get("content-type") ?? "";
    if (contentType.includes("multipart/form-data")) {
        const formData = await req.formData();
        const clubId = Number(getOptionalFormString(formData, "clubId"));
        if (!Number.isInteger(clubId) || clubId <= 0) {
            return { error: "Invalid payload", status: 400 } as const;
        }
        return {
            data: {
                clubId,
                iconImageUrl: getOptionalFormString(formData, "iconImageUrl"),
                heroImageUrl: getOptionalFormString(formData, "heroImageUrl"),
                iconFile: getOptionalFormFile(formData, "iconFile"),
                heroFile: getOptionalFormFile(formData, "heroFile"),
            } satisfies NormalizedRequest,
        } as const;
    }

    const parsed = requestSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return {
            error: "Invalid payload",
            issues: parsed.error.issues,
            status: 400,
        } as const;
    }
    return { data: parsed.data satisfies NormalizedRequest } as const;
}

function getSlotInputs(data: NormalizedRequest, slot: ImageSlot) {
    if (slot === "icon") {
        return { url: data.iconImageUrl, file: data.iconFile };
    }
    return { url: data.heroImageUrl, file: data.heroFile };
}

function validateRequestSlots(data: NormalizedRequest) {
    const slots: ImageSlot[] = [];
    for (const slot of ["icon", "hero"] as const) {
        const { url, file } = getSlotInputs(data, slot);
        if (url && file) {
            const article = slot === "icon" ? "an" : "a";
            return {
                error: `Provide either ${article} ${slot} URL or ${slot} file, not both`,
                slots,
            };
        }
        if (url || file) slots.push(slot);
    }
    if (slots.length === 0) {
        return { error: "Provide an icon or hero image to preview", slots };
    }
    return { slots };
}

async function loadImage(
    data: NormalizedRequest,
    slot: ImageSlot,
): Promise<DownloadedComedianImage> {
    const { url, file } = getSlotInputs(data, slot);
    return file ? readUploadedComedianImage(file) : downloadComedianImage(url!);
}

export async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const normalized = await normalizeRequest(req);
    if ("error" in normalized) {
        return NextResponse.json(
            {
                error: normalized.error,
                ...("issues" in normalized
                    ? { issues: normalized.issues }
                    : {}),
            },
            { status: normalized.status },
        );
    }
    const data: NormalizedRequest = normalized.data;
    const slotValidation = validateRequestSlots(data);
    if (slotValidation.error) {
        return NextResponse.json(
            { error: slotValidation.error },
            { status: 400 },
        );
    }

    const club = await db.club.findUnique({
        where: { id: data.clubId },
        select: { id: true },
    });
    if (!club) {
        return NextResponse.json({ error: "Club not found" }, { status: 404 });
    }

    try {
        const iconInput = getSlotInputs(data, "icon");
        const heroInput = getSlotInputs(data, "hero");
        const icon =
            iconInput.url || iconInput.file
                ? await loadImage(data, "icon")
                : undefined;
        const hero =
            heroInput.url || heroInput.file
                ? await loadImage(data, "hero")
                : undefined;
        const primaryImage = icon ?? hero;
        if (!primaryImage) {
            return NextResponse.json(
                { error: "Provide an icon or hero image to preview" },
                { status: 400 },
            );
        }
        const variants = await generateClubImageVariants({
            icon: icon ?? primaryImage,
            hero,
        });

        const warnings: string[] = [];
        if (hero && (hero.width < HERO_WIDTH || hero.height < HERO_HEIGHT)) {
            warnings.push(
                `Hero source ${hero.width}x${hero.height} is below preferred hero ${HERO_WIDTH}x${HERO_HEIGHT}; hero crop may be lower quality`,
            );
        }

        return NextResponse.json({
            ok: true,
            clubId: club.id,
            source: {
                iconImageUrl: icon?.sourceUrl ?? null,
                heroImageUrl: hero?.sourceUrl ?? null,
                iconMimeType: icon?.mimeType ?? null,
                heroMimeType: hero?.mimeType ?? null,
                iconWidth: icon?.width ?? null,
                iconHeight: icon?.height ?? null,
                heroWidth: hero?.width ?? null,
                heroHeight: hero?.height ?? null,
            },
            iconDataUrl: icon
                ? `data:image/png;base64,${variants.iconBuffer.toString("base64")}`
                : null,
            heroDataUrl: variants.heroBuffer
                ? `data:image/jpeg;base64,${variants.heroBuffer.toString("base64")}`
                : null,
            warnings,
        });
    } catch (error) {
        if (error instanceof ComedianImageDownloadError) {
            return NextResponse.json(
                { error: error.message, code: error.code },
                { status: 400 },
            );
        }
        console.error("Admin club image preview failed:", error);
        return NextResponse.json(
            { error: "Preview generation failed" },
            { status: 500 },
        );
    }
}
