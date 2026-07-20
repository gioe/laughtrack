"use client";

import type { AdminClubListItem } from "@/lib/admin/clubManagement";
import { validateComedianImageFile } from "@/lib/admin/comedianImageClientValidation";
import type { ReactNode } from "react";
import { createContext, useContext, useMemo, useState } from "react";
import { adminRequest } from "../shared/adminRequest";

export type AdminClubStatus = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

export type AdminClubDraft = {
    status: string;
    visible: boolean;
    clubType: string;
    closedAt: string;
};

export type AdminClubManualImage = {
    icon: string;
    iconFile: File | null;
};

export type AdminClubRowStoreValue = {
    drafts: Record<number, AdminClubDraft>;
    setDrafts: React.Dispatch<
        React.SetStateAction<Record<number, AdminClubDraft>>
    >;
    nameEdits: Record<number, string>;
    setNameEdits: React.Dispatch<React.SetStateAction<Record<number, string>>>;
    manualImages: Record<number, AdminClubManualImage>;
    setManualImages: React.Dispatch<
        React.SetStateAction<Record<number, AdminClubManualImage>>
    >;
    imageStatusByClub: Record<number, AdminClubStatus>;
    setImageStatusByClub: React.Dispatch<
        React.SetStateAction<Record<number, AdminClubStatus>>
    >;
    pendingId: number | null;
    setPendingId: React.Dispatch<React.SetStateAction<number | null>>;
    setStatus: React.Dispatch<React.SetStateAction<AdminClubStatus>>;
    onClubChange: (club: AdminClubListItem) => void;
};

const RowStoreContext = createContext<AdminClubRowStoreValue | null>(null);

function dateInputValue(iso: string | null) {
    return iso ? iso.slice(0, 10) : "";
}

function initialDraft(club: AdminClubListItem): AdminClubDraft {
    return {
        status: club.status,
        visible: club.visible,
        clubType: club.clubType,
        closedAt: dateInputValue(club.closedAt),
    };
}

function currentIconUrl(club: AdminClubListItem) {
    return club.activeImageAsset?.iconUrl ?? club.iconUrl;
}

function initialManualImage(club: AdminClubListItem): AdminClubManualImage {
    return { icon: currentIconUrl(club), iconFile: null };
}

function normalizedClubName(name: string) {
    return name.trim().replace(/\s+/g, " ");
}

export function useAdminClubRowStore(
    onClubChange: (club: AdminClubListItem) => void,
) {
    const [drafts, setDrafts] = useState<Record<number, AdminClubDraft>>({});
    const [nameEdits, setNameEdits] = useState<Record<number, string>>({});
    const [manualImages, setManualImages] = useState<
        Record<number, AdminClubManualImage>
    >({});
    const [imageStatusByClub, setImageStatusByClub] = useState<
        Record<number, AdminClubStatus>
    >({});
    const [pendingId, setPendingId] = useState<number | null>(null);
    const [status, setStatus] = useState<AdminClubStatus>({ kind: "idle" });

    const contextValue = useMemo<AdminClubRowStoreValue>(
        () => ({
            drafts,
            setDrafts,
            nameEdits,
            setNameEdits,
            manualImages,
            setManualImages,
            imageStatusByClub,
            setImageStatusByClub,
            pendingId,
            setPendingId,
            setStatus,
            onClubChange,
        }),
        [
            drafts,
            imageStatusByClub,
            manualImages,
            nameEdits,
            onClubChange,
            pendingId,
        ],
    );

    return { contextValue, status, pendingId };
}

export function AdminClubRowControllerProvider({
    value,
    children,
}: {
    value: AdminClubRowStoreValue;
    children: ReactNode;
}) {
    return (
        <RowStoreContext.Provider value={value}>
            {children}
        </RowStoreContext.Provider>
    );
}

function useRowStore() {
    const store = useContext(RowStoreContext);
    if (!store) {
        throw new Error(
            "useAdminClubRowController must be used within AdminClubRowControllerProvider",
        );
    }
    return store;
}

export type AdminClubRowController = {
    draft: AdminClubDraft;
    name: string;
    image: AdminClubManualImage;
    imageStatus?: AdminClubStatus;
    statusDirty: boolean;
    nameDirty: boolean;
    imageDirty: boolean;
    disabled: boolean;
    pending: boolean;
    currentIconUrl: string;
    setName: (value: string) => void;
    patchDraft: (patch: Partial<AdminClubDraft>) => void;
    patchImage: (patch: Partial<AdminClubManualImage>) => void;
    saveName: () => Promise<void>;
    saveStatus: () => Promise<void>;
    stageImage: (file: File) => Promise<void>;
    discardStagedFile: () => void;
    publishImage: () => Promise<void>;
    removeImage: () => Promise<void>;
};

export function useAdminClubRowController(
    club: AdminClubListItem,
): AdminClubRowController {
    const store = useRowStore();
    const draft = store.drafts[club.id] ?? initialDraft(club);
    const name = Object.hasOwn(store.nameEdits, club.id)
        ? store.nameEdits[club.id]
        : club.name;
    const image = store.manualImages[club.id] ?? initialManualImage(club);
    const canonicalIconUrl = currentIconUrl(club);
    const statusDirty =
        draft.status !== club.status ||
        draft.visible !== club.visible ||
        draft.clubType !== club.clubType ||
        draft.closedAt !== dateInputValue(club.closedAt);
    const nameDirty = normalizedClubName(name) !== club.name;
    const imageDirty = Boolean(
        image.iconFile ||
            (image.icon.trim() && image.icon.trim() !== canonicalIconUrl),
    );

    function setName(value: string) {
        store.setNameEdits((current) => ({
            ...current,
            [club.id]: value,
        }));
    }

    function patchDraft(patch: Partial<AdminClubDraft>) {
        store.setDrafts((current) => ({
            ...current,
            [club.id]: {
                ...(current[club.id] ?? initialDraft(club)),
                ...patch,
            },
        }));
    }

    function patchImage(patch: Partial<AdminClubManualImage>) {
        store.setManualImages((current) => ({
            ...current,
            [club.id]: {
                ...(current[club.id] ?? initialManualImage(club)),
                ...patch,
            },
        }));
    }

    function beginMutation() {
        store.setStatus({ kind: "idle" });
        store.setPendingId(club.id);
    }

    function failMutation(error: unknown) {
        store.setPendingId(null);
        store.setStatus({
            kind: "error",
            message: error instanceof Error ? error.message : "Network error",
        });
    }

    function clearDraft() {
        store.setDrafts((current) => {
            const next = { ...current };
            delete next[club.id];
            return next;
        });
    }

    function clearName() {
        store.setNameEdits((current) => {
            const next = { ...current };
            delete next[club.id];
            return next;
        });
    }

    async function saveStatus() {
        beginMutation();
        let body: { club: AdminClubListItem };
        try {
            body = await adminRequest<{ club: AdminClubListItem }>(
                `/api/admin/clubs/${club.id}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        status: draft.status,
                        visible: draft.visible,
                        clubType: draft.clubType,
                        closedAt: draft.closedAt || null,
                    }),
                },
            );
        } catch (error) {
            failMutation(error);
            return;
        }

        store.setPendingId(null);
        store.onClubChange(body.club);
        clearDraft();
        store.setStatus({ kind: "ok", message: `${club.name} saved.` });
    }

    async function saveName() {
        const normalizedName = normalizedClubName(name);
        if (!normalizedName || normalizedName === club.name) return;

        beginMutation();
        let body: { club: AdminClubListItem };
        try {
            body = await adminRequest<{ club: AdminClubListItem }>(
                `/api/admin/clubs/${club.id}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name: normalizedName }),
                },
            );
        } catch (error) {
            failMutation(error);
            return;
        }

        store.setPendingId(null);
        store.onClubChange(body.club);
        clearName();
        store.setStatus({ kind: "ok", message: `${club.name} renamed.` });
    }

    async function stageImage(file: File) {
        const result = await validateComedianImageFile(file, "headshot");
        if (!result.ok) {
            const imageStatus = {
                kind: "error",
                message: result.reason,
            } as const;
            store.setStatus(imageStatus);
            store.setImageStatusByClub((current) => ({
                ...current,
                [club.id]: imageStatus,
            }));
            return;
        }
        patchImage({ iconFile: file });
        store.setStatus({ kind: "idle" });
        store.setImageStatusByClub((current) => ({
            ...current,
            [club.id]: {
                kind: "ok",
                message: `Thumbnail staged at ${file.name}. Click "Publish to Bunny" to commit, or "Discard" to remove.`,
            },
        }));
    }

    function discardStagedFile() {
        patchImage({ iconFile: null });
        store.setImageStatusByClub((current) => {
            const next = { ...current };
            delete next[club.id];
            return next;
        });
    }

    async function publishImage() {
        beginMutation();
        let body: { asset: AdminClubListItem["activeImageAsset"] };
        try {
            if (image.iconFile) {
                const formData = new FormData();
                formData.set("clubId", String(club.id));
                formData.set("iconFile", image.iconFile);
                body = await adminRequest<{
                    asset: AdminClubListItem["activeImageAsset"];
                }>("/api/admin/clubs/images/publish", {
                    method: "POST",
                    body: formData,
                });
            } else {
                body = await adminRequest<{
                    asset: AdminClubListItem["activeImageAsset"];
                }>("/api/admin/clubs/images/publish", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        clubId: club.id,
                        iconImageUrl: image.icon.trim(),
                    }),
                });
            }
        } catch (error) {
            failMutation(error);
            return;
        }

        store.setPendingId(null);
        const asset = body.asset;
        const updated: AdminClubListItem = {
            ...club,
            hasImage: true,
            iconUrl: asset?.iconUrl ?? club.iconUrl,
            heroUrl: asset?.heroUrl ?? club.heroUrl,
            activeImageAsset: asset,
        };
        store.onClubChange(updated);
        store.setManualImages((current) => ({
            ...current,
            [club.id]: {
                icon: asset?.iconUrl ?? updated.iconUrl,
                iconFile: null,
            },
        }));
        const imageStatus = {
            kind: "ok",
            message: `${club.name} thumbnail updated.`,
        } as const;
        store.setImageStatusByClub((current) => ({
            ...current,
            [club.id]: imageStatus,
        }));
        store.setStatus(imageStatus);
    }

    async function removeImage() {
        beginMutation();
        let body: { asset: AdminClubListItem["activeImageAsset"] };
        try {
            body = await adminRequest<{
                asset: AdminClubListItem["activeImageAsset"];
            }>("/api/admin/clubs/images", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ clubId: club.id }),
            });
        } catch (error) {
            failMutation(error);
            return;
        }

        store.setPendingId(null);
        const asset = body.asset;
        const updated: AdminClubListItem = {
            ...club,
            hasImage: false,
            iconUrl: "/placeholders/club-placeholder.svg",
            heroUrl: asset?.heroUrl ?? club.heroUrl,
            activeImageAsset: asset,
        };
        store.onClubChange(updated);
        store.setManualImages((current) => ({
            ...current,
            [club.id]: { icon: updated.iconUrl, iconFile: null },
        }));
        const imageStatus = {
            kind: "ok",
            message: `${club.name} thumbnail removed.`,
        } as const;
        store.setImageStatusByClub((current) => ({
            ...current,
            [club.id]: imageStatus,
        }));
        store.setStatus(imageStatus);
    }

    return {
        draft,
        name,
        image,
        imageStatus: store.imageStatusByClub[club.id],
        statusDirty,
        nameDirty,
        imageDirty,
        disabled: store.pendingId !== null,
        pending: store.pendingId === club.id,
        currentIconUrl: canonicalIconUrl,
        setName,
        patchDraft,
        patchImage,
        saveName,
        saveStatus,
        stageImage,
        discardStagedFile,
        publishImage,
        removeImage,
    };
}
