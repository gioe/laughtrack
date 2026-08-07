"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
    DISCOVERY_PLATFORMS,
    DiscoveryRailPolicyUpdateSchema,
    type DiscoveryPlatform,
    type DiscoveryRailKey,
    type DiscoveryRailPolicyDto,
} from "@/lib/discovery/railPolicy";
import {
    getDiscoveryRailCycleIndex,
    selectDiscoveryRailPlan,
    type DiscoveryRailPayloadMap,
} from "@/lib/discovery/railSelector";
import { Button } from "@/ui/components/ui/button";
import { adminRequest } from "../shared/adminRequest";

type CatalogEntry = {
    key: DiscoveryRailKey;
    label: string;
    contentKind: string;
    requiresAuth: boolean;
    supportedPlatforms: DiscoveryPlatform[];
    catalogVersion: number;
};

type PlatformPolicyView = DiscoveryRailPolicyDto & {
    provenance: "stored" | "built_in_default";
    updatedAt: string | null;
    updatedBy: {
        profileId: string;
        name: string | null;
        email: string;
    } | null;
};

type DiscoveryRailAdminResponse = {
    catalogVersion: number;
    catalog: CatalogEntry[];
    platforms: PlatformPolicyView[];
};

type PolicyMap<T> = Partial<Record<DiscoveryPlatform, T>>;

type EditorStatus = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

const PLATFORM_LABELS: Record<DiscoveryPlatform, string> = {
    web: "Web",
    ios: "iOS",
    android: "Android",
};

const PREVIEW_ACTOR_KEY = "admin-policy-preview";

function policyDraft(policy: PlatformPolicyView): DiscoveryRailPolicyDto {
    return {
        platform: policy.platform,
        catalogVersion: policy.catalogVersion,
        version: policy.version,
        cycleCadenceHours: policy.cycleCadenceHours,
        rails: structuredClone(policy.rails),
    };
}

function previewPolicy(
    saved: PlatformPolicyView,
    draft: DiscoveryRailPolicyDto,
): DiscoveryRailPolicyDto | null {
    const parsed = DiscoveryRailPolicyUpdateSchema.safeParse({
        platform: draft.platform,
        catalogVersion: draft.catalogVersion,
        expectedVersion: saved.version,
        cycleCadenceHours: draft.cycleCadenceHours,
        rails: draft.rails,
    });
    if (!parsed.success) return null;

    return {
        platform: parsed.data.platform,
        catalogVersion: parsed.data.catalogVersion,
        version: saved.version + 1,
        cycleCadenceHours: parsed.data.cycleCadenceHours,
        rails: parsed.data.rails as DiscoveryRailPolicyDto["rails"],
    };
}

function normalizeSlotPositions(
    rails: DiscoveryRailPolicyDto["rails"],
): DiscoveryRailPolicyDto["rails"] {
    const positions = [...new Set(rails.map((rail) => rail.position))].sort(
        (left, right) => left - right,
    );
    const normalized = new Map(
        positions.map((position, index) => [position, index]),
    );
    return rails.map((rail) => ({
        ...rail,
        position: normalized.get(rail.position) ?? rail.position,
    }));
}

function formatDateTime(value: string | null): string {
    if (!value) return "Not recorded";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    }).format(date);
}

function policyIsChanged(
    saved: PlatformPolicyView,
    draft: DiscoveryRailPolicyDto,
): boolean {
    return (
        saved.cycleCadenceHours !== draft.cycleCadenceHours ||
        JSON.stringify(saved.rails) !== JSON.stringify(draft.rails)
    );
}

export default function AdminDiscoveryRailPolicyEditor() {
    const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
    const [savedPolicies, setSavedPolicies] = useState<
        PolicyMap<PlatformPolicyView>
    >({});
    const [drafts, setDrafts] = useState<PolicyMap<DiscoveryRailPolicyDto>>({});
    const [lastValidPreviews, setLastValidPreviews] = useState<
        PolicyMap<DiscoveryRailPolicyDto>
    >({});
    const [selectedPlatform, setSelectedPlatform] =
        useState<DiscoveryPlatform>("web");
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [requiresReload, setRequiresReload] = useState(false);
    const [status, setStatus] = useState<EditorStatus>({ kind: "idle" });
    const [previewObservedAt] = useState(() => Date.now());

    const loadPolicies = useCallback(async (clearStatus = true) => {
        setIsLoading(true);
        if (clearStatus) setStatus({ kind: "idle" });
        try {
            const data = await adminRequest<DiscoveryRailAdminResponse>(
                "/api/admin/discovery-rails",
                undefined,
                {
                    httpErrorMessage: "Unable to load Discover rail policies",
                    networkErrorMessage:
                        "Unable to load Discover rail policies. Check your connection and try again.",
                },
            );
            const nextSaved: PolicyMap<PlatformPolicyView> = {};
            const nextDrafts: PolicyMap<DiscoveryRailPolicyDto> = {};
            const nextPreviews: PolicyMap<DiscoveryRailPolicyDto> = {};
            for (const policy of data.platforms) {
                nextSaved[policy.platform] = policy;
                const draft = policyDraft(policy);
                nextDrafts[policy.platform] = draft;
                nextPreviews[policy.platform] =
                    previewPolicy(policy, draft) ?? draft;
            }
            setCatalog(data.catalog);
            setSavedPolicies(nextSaved);
            setDrafts(nextDrafts);
            setLastValidPreviews(nextPreviews);
            setRequiresReload(false);
            return true;
        } catch (error) {
            setStatus({
                kind: "error",
                message:
                    error instanceof Error
                        ? error.message
                        : "Unable to load Discover rail policies",
            });
            return false;
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadPolicies();
    }, [loadPolicies]);

    useEffect(() => {
        setLastValidPreviews((current) => {
            const next = { ...current };
            for (const platform of DISCOVERY_PLATFORMS) {
                const saved = savedPolicies[platform];
                const draft = drafts[platform];
                if (!saved || !draft) continue;
                const valid = previewPolicy(saved, draft);
                if (valid) next[platform] = valid;
            }
            return next;
        });
    }, [drafts, savedPolicies]);

    const saved = savedPolicies[selectedPlatform];
    const draft = drafts[selectedPlatform];
    const lastValidPreview = lastValidPreviews[selectedPlatform];

    const validation = useMemo(() => {
        if (!saved || !draft) return null;
        return DiscoveryRailPolicyUpdateSchema.safeParse({
            platform: draft.platform,
            catalogVersion: draft.catalogVersion,
            expectedVersion: saved.version,
            cycleCadenceHours: draft.cycleCadenceHours,
            rails: draft.rails,
        });
    }, [draft, saved]);

    const labels = useMemo(
        () => new Map(catalog.map((entry) => [entry.key, entry.label])),
        [catalog],
    );

    const previewPlans = useMemo(() => {
        if (!lastValidPreview) return null;
        const payloads: DiscoveryRailPayloadMap = {};
        catalog.forEach((entry) => {
            payloads[entry.key] = {
                payloadKey: entry.key,
                items: [{ id: `preview-${entry.key}` }],
            };
        });
        const cycleIndex = getDiscoveryRailCycleIndex(
            previewObservedAt,
            lastValidPreview.cycleCadenceHours,
        );
        return {
            current: selectDiscoveryRailPlan({
                policy: lastValidPreview,
                actorKey: PREVIEW_ACTOR_KEY,
                cycleIndex,
                payloads,
            }),
            next: selectDiscoveryRailPlan({
                policy: lastValidPreview,
                actorKey: PREVIEW_ACTOR_KEY,
                cycleIndex: cycleIndex + 1,
                payloads,
            }),
        };
    }, [catalog, lastValidPreview, previewObservedAt]);

    function updateDraft(
        updater: (policy: DiscoveryRailPolicyDto) => DiscoveryRailPolicyDto,
    ) {
        setDrafts((current) => {
            const currentDraft = current[selectedPlatform];
            if (!currentDraft) return current;
            return {
                ...current,
                [selectedPlatform]: updater(currentDraft),
            };
        });
        setStatus({ kind: "idle" });
    }

    function updateRail(
        railKey: DiscoveryRailKey,
        update: (
            rail: DiscoveryRailPolicyDto["rails"][number],
        ) => DiscoveryRailPolicyDto["rails"][number],
    ) {
        updateDraft((policy) => ({
            ...policy,
            rails: policy.rails.map((rail) =>
                rail.railKey === railKey ? update(rail) : rail,
            ),
        }));
    }

    function moveSlot(position: number, direction: -1 | 1) {
        updateDraft((policy) => {
            const positions = [
                ...new Set(policy.rails.map((rail) => rail.position)),
            ].sort((left, right) => left - right);
            const sourceIndex = positions.indexOf(position);
            const target = positions[sourceIndex + direction];
            if (target === undefined) return policy;
            return {
                ...policy,
                rails: policy.rails.map((rail) => ({
                    ...rail,
                    position:
                        rail.position === position
                            ? target
                            : rail.position === target
                              ? position
                              : rail.position,
                })),
            };
        });
    }

    function pinRail(railKey: DiscoveryRailKey) {
        updateDraft((policy) => {
            const selected = policy.rails.find(
                (rail) => rail.railKey === railKey,
            );
            if (!selected) return policy;
            const sharesSlot = policy.rails.some(
                (rail) =>
                    rail.railKey !== railKey &&
                    rail.position === selected.position,
            );
            const nextPosition = sharesSlot
                ? selected.position + 0.5
                : selected.position;
            return {
                ...policy,
                rails: normalizeSlotPositions(
                    policy.rails.map((rail) =>
                        rail.railKey === railKey
                            ? {
                                  ...rail,
                                  rotationPool: null,
                                  position: nextPosition,
                                  weight: 1,
                              }
                            : rail,
                    ),
                ),
            };
        });
    }

    function groupRail(railKey: DiscoveryRailKey, rawGroup: string) {
        const rotationPool = rawGroup.trim();
        if (!rotationPool) {
            pinRail(railKey);
            return;
        }

        updateDraft((policy) => {
            const selected = policy.rails.find(
                (rail) => rail.railKey === railKey,
            );
            if (!selected || selected.rotationPool === rotationPool) {
                return policy;
            }
            const targetMember = policy.rails.find(
                (rail) =>
                    rail.railKey !== railKey &&
                    rail.rotationPool === rotationPool,
            );
            const sharesSourceSlot = policy.rails.some(
                (rail) =>
                    rail.railKey !== railKey &&
                    rail.position === selected.position,
            );
            const targetPosition =
                targetMember?.position ??
                (sharesSourceSlot
                    ? selected.position + 0.5
                    : selected.position);
            return {
                ...policy,
                rails: normalizeSlotPositions(
                    policy.rails.map((rail) =>
                        rail.railKey === railKey
                            ? {
                                  ...rail,
                                  rotationPool,
                                  position: targetPosition,
                              }
                            : rail,
                    ),
                ),
            };
        });
    }

    function resetDraft() {
        if (!saved) return;
        const reset = policyDraft(saved);
        setDrafts((current) => ({
            ...current,
            [selectedPlatform]: reset,
        }));
        setLastValidPreviews((current) => ({
            ...current,
            [selectedPlatform]: previewPolicy(saved, reset) ?? reset,
        }));
        setStatus({ kind: "idle" });
    }

    async function savePolicy() {
        if (!saved || !draft || !validation?.success) {
            setStatus({
                kind: "error",
                message: "Fix the policy validation errors before saving.",
            });
            return;
        }

        setIsSaving(true);
        setStatus({ kind: "idle" });
        try {
            await adminRequest("/api/admin/discovery-rails", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(validation.data),
            });
            const reloaded = await loadPolicies(false);
            if (reloaded) {
                setStatus({
                    kind: "ok",
                    message: `${PLATFORM_LABELS[selectedPlatform]} policy saved.`,
                });
            } else {
                setRequiresReload(true);
                setStatus({
                    kind: "error",
                    message:
                        "The policy was saved, but its latest version could not be reloaded. Reload policies before making more changes.",
                });
            }
        } catch (error) {
            const message =
                error instanceof Error ? error.message : "Save failed";
            const conflict = message.toLowerCase().includes("changed");
            setStatus({
                kind: "error",
                message: conflict
                    ? `${message}. Reload policies to review the newer version before trying again. Your last saved policy is unchanged.`
                    : `${message}. Your last saved policy is unchanged; retry or reload policies.`,
            });
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading && !saved) {
        return (
            <div
                role="status"
                aria-live="polite"
                className="rounded-md border border-copper/20 bg-surface-elevated p-5 font-dmSans text-body text-foreground"
            >
                Loading Discover rail policies…
            </div>
        );
    }

    if (!saved || !draft) {
        return (
            <div className="rounded-md border border-red-700/30 bg-red-50 p-5 font-dmSans text-red-900">
                <p role="alert">{status.message ?? "No policy data found."}</p>
                <Button
                    type="button"
                    variant="outline"
                    className="mt-3"
                    onClick={() => void loadPolicies()}
                >
                    Reload policies
                </Button>
            </div>
        );
    }

    const slots = [...new Set(draft.rails.map((rail) => rail.position))]
        .sort((left, right) => left - right)
        .map((position) => ({
            position,
            rails: draft.rails.filter((rail) => rail.position === position),
        }));
    const hasChanges = policyIsChanged(saved, draft);
    const validationIssues =
        validation && !validation.success ? validation.error.issues : [];

    return (
        <div className="space-y-6">
            <section aria-labelledby="platform-policy-heading">
                <div className="flex flex-wrap items-end justify-between gap-3">
                    <div>
                        <h2
                            id="platform-policy-heading"
                            className="font-urbanist-bold text-h3 text-foreground"
                        >
                            Platform policies
                        </h2>
                        <p className="mt-1 font-dmSans text-body text-muted-foreground">
                            Select a platform to edit its effective Discover
                            order and rotation rules.
                        </p>
                    </div>
                    <Button
                        type="button"
                        variant="outline"
                        disabled={isLoading || isSaving}
                        onClick={() => void loadPolicies()}
                    >
                        Reload policies
                    </Button>
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-3 lg:grid-cols-3">
                    {DISCOVERY_PLATFORMS.map((platform) => {
                        const policy = savedPolicies[platform];
                        if (!policy) return null;
                        const updater =
                            policy.updatedBy?.name ||
                            policy.updatedBy?.email ||
                            "an unknown admin";
                        return (
                            <button
                                key={platform}
                                type="button"
                                aria-pressed={selectedPlatform === platform}
                                onClick={() => setSelectedPlatform(platform)}
                                className={`rounded-md border p-4 text-left outline-none focus-visible:ring-2 focus-visible:ring-copper/40 ${
                                    selectedPlatform === platform
                                        ? "border-copper bg-copper/10"
                                        : "border-copper/20 bg-surface-elevated hover:bg-surface-muted"
                                }`}
                            >
                                <span className="block font-urbanist-bold text-h3 text-foreground">
                                    {PLATFORM_LABELS[platform]}
                                </span>
                                <span className="mt-2 block font-dmSans text-caption text-muted-foreground">
                                    Version {policy.version} ·{" "}
                                    {policy.cycleCadenceHours}-hour cadence
                                </span>
                                <span className="mt-1 block font-dmSans text-caption font-semibold text-foreground">
                                    {policy.provenance === "stored"
                                        ? "Stored admin policy"
                                        : "Built-in default policy"}
                                </span>
                                <span className="mt-1 block font-dmSans text-caption text-muted-foreground">
                                    {policy.provenance === "stored"
                                        ? `Updated ${formatDateTime(policy.updatedAt)} by ${updater}`
                                        : "No admin update recorded; using the built-in policy."}
                                </span>
                            </button>
                        );
                    })}
                </div>
            </section>

            {status.kind !== "idle" ? (
                <p
                    role={status.kind === "error" ? "alert" : "status"}
                    aria-live="polite"
                    className={
                        status.kind === "error"
                            ? "rounded-md border border-red-700/30 bg-red-50 px-4 py-3 font-dmSans text-body font-semibold text-red-900"
                            : "rounded-md border border-green-700/30 bg-green-50 px-4 py-3 font-dmSans text-body font-semibold text-green-900"
                    }
                >
                    {status.message}
                </p>
            ) : null}

            <section
                aria-labelledby="policy-settings-heading"
                className="rounded-md border border-copper/20 bg-surface-elevated p-4 md:p-5 lg:p-5"
            >
                <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between lg:flex-row lg:items-end lg:justify-between">
                    <div>
                        <h2
                            id="policy-settings-heading"
                            className="font-urbanist-bold text-h3 text-foreground"
                        >
                            {PLATFORM_LABELS[selectedPlatform]} policy settings
                        </h2>
                        <p className="mt-1 font-dmSans text-caption text-muted-foreground">
                            Catalog {draft.catalogVersion} · saved version{" "}
                            {saved.version}
                        </p>
                    </div>
                    <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                        Rotation cadence (hours)
                        <input
                            type="number"
                            min={1}
                            max={168}
                            step={1}
                            value={draft.cycleCadenceHours}
                            onChange={(event) =>
                                updateDraft((policy) => ({
                                    ...policy,
                                    cycleCadenceHours: Number(
                                        event.target.value,
                                    ),
                                }))
                            }
                            className="w-40 rounded-md border border-input bg-background px-3 py-2 font-normal text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                        />
                    </label>
                </div>
            </section>

            {validationIssues.length > 0 ? (
                <div
                    role="alert"
                    aria-live="polite"
                    className="rounded-md border border-red-700/30 bg-red-50 px-4 py-3 font-dmSans text-body text-red-900"
                >
                    <p className="font-semibold">
                        This draft is not valid yet. The preview below keeps the
                        last valid arrangement.
                    </p>
                    <ul className="mt-2 list-disc space-y-1 pl-5">
                        {validationIssues.map((issue, index) => {
                            const railIndex =
                                issue.path[0] === "rails" &&
                                typeof issue.path[1] === "number"
                                    ? issue.path[1]
                                    : null;
                            const rail =
                                railIndex === null
                                    ? null
                                    : draft.rails[railIndex];
                            return (
                                <li key={`${issue.path.join("-")}-${index}`}>
                                    {rail
                                        ? `${labels.get(rail.railKey) ?? rail.railKey}: `
                                        : ""}
                                    {issue.message}
                                </li>
                            );
                        })}
                    </ul>
                </div>
            ) : null}

            <section aria-labelledby="rail-order-heading" className="space-y-3">
                <div>
                    <h2
                        id="rail-order-heading"
                        className="font-urbanist-bold text-h3 text-foreground"
                    >
                        Rail order and placement
                    </h2>
                    <p className="mt-1 font-dmSans text-body text-muted-foreground">
                        Fixed rails always occupy their slot. Rails with the
                        same rotation group share one slot and are selected by
                        weight each cycle.
                    </p>
                </div>

                {slots.map((slot, slotIndex) => {
                    const pool = slot.rails[0]?.rotationPool;
                    const slotName = pool
                        ? `Rotation group ${pool}`
                        : (labels.get(slot.rails[0].railKey) ??
                          slot.rails[0].railKey);
                    return (
                        <div
                            key={slot.position}
                            className="overflow-hidden rounded-md border border-copper/20 bg-surface-elevated"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-copper/15 bg-cedar px-4 py-3">
                                <div>
                                    <p className="font-dmSans text-caption font-semibold uppercase text-copper">
                                        Slot {slotIndex + 1}
                                    </p>
                                    <h3 className="font-urbanist-bold text-body text-foreground">
                                        {slotName}
                                    </h3>
                                </div>
                                <div className="flex gap-2">
                                    <Button
                                        type="button"
                                        size="sm"
                                        variant="outline"
                                        aria-label={`Move ${slotName} up`}
                                        disabled={slotIndex === 0}
                                        onClick={() =>
                                            moveSlot(slot.position, -1)
                                        }
                                    >
                                        Move up
                                    </Button>
                                    <Button
                                        type="button"
                                        size="sm"
                                        variant="outline"
                                        aria-label={`Move ${slotName} down`}
                                        disabled={
                                            slotIndex === slots.length - 1
                                        }
                                        onClick={() =>
                                            moveSlot(slot.position, 1)
                                        }
                                    >
                                        Move down
                                    </Button>
                                </div>
                            </div>

                            <div className="divide-y divide-copper/10">
                                {slot.rails.map((rail) => {
                                    const label =
                                        labels.get(rail.railKey) ??
                                        rail.railKey;
                                    return (
                                        <div
                                            key={rail.railKey}
                                            className="grid gap-4 p-4 lg:grid-cols-[minmax(220px,1fr)_minmax(220px,1fr)_150px_auto] lg:items-end"
                                        >
                                            <div>
                                                <p className="font-urbanist-bold text-body text-foreground">
                                                    {label}
                                                </p>
                                                <p className="mt-1 font-dmSans text-caption text-muted-foreground">
                                                    {rail.rotationPool
                                                        ? `Rotating in ${rail.rotationPool}`
                                                        : "Fixed placement"}
                                                </p>
                                                <label className="mt-3 inline-flex items-center gap-2 font-dmSans text-body font-semibold text-foreground">
                                                    <input
                                                        type="checkbox"
                                                        checked={rail.enabled}
                                                        onChange={(event) =>
                                                            updateRail(
                                                                rail.railKey,
                                                                (current) => ({
                                                                    ...current,
                                                                    enabled:
                                                                        event
                                                                            .target
                                                                            .checked,
                                                                }),
                                                            )
                                                        }
                                                        className="h-4 w-4 rounded border-strong text-copper focus:ring-copper/30"
                                                    />
                                                    Enable {label}
                                                </label>
                                            </div>

                                            <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                                                Rotation group for {label}
                                                <input
                                                    type="text"
                                                    value={
                                                        rail.rotationPool ?? ""
                                                    }
                                                    placeholder="Leave blank for fixed"
                                                    onChange={(event) =>
                                                        groupRail(
                                                            rail.railKey,
                                                            event.target.value,
                                                        )
                                                    }
                                                    className="rounded-md border border-input bg-background px-3 py-2 font-normal text-foreground outline-none placeholder:text-muted-foreground focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                />
                                            </label>

                                            <label className="grid gap-1 font-dmSans text-body font-semibold text-foreground">
                                                Weight for {label}
                                                <input
                                                    type="number"
                                                    min={1}
                                                    max={100}
                                                    step={1}
                                                    disabled={
                                                        rail.rotationPool ===
                                                        null
                                                    }
                                                    value={rail.weight}
                                                    onChange={(event) =>
                                                        updateRail(
                                                            rail.railKey,
                                                            (current) => ({
                                                                ...current,
                                                                weight: Number(
                                                                    event.target
                                                                        .value,
                                                                ),
                                                            }),
                                                        )
                                                    }
                                                    className="rounded-md border border-input bg-background px-3 py-2 font-normal text-foreground outline-none focus:border-copper focus:ring-2 focus:ring-copper/30 disabled:bg-surface-muted disabled:text-muted-foreground"
                                                />
                                            </label>

                                            {rail.rotationPool ? (
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    aria-label={`Pin ${label}`}
                                                    onClick={() =>
                                                        pinRail(rail.railKey)
                                                    }
                                                >
                                                    Pin as fixed
                                                </Button>
                                            ) : (
                                                <span className="rounded-md border border-copper/20 bg-surface-muted px-3 py-2 text-center font-dmSans text-caption font-semibold text-muted-foreground">
                                                    Fixed
                                                </span>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    );
                })}
            </section>

            <section aria-labelledby="rotation-preview-heading">
                <div className="flex flex-wrap items-end justify-between gap-3">
                    <div>
                        <h2
                            id="rotation-preview-heading"
                            className="font-urbanist-bold text-h3 text-foreground"
                        >
                            Rotation preview
                        </h2>
                        <p className="mt-1 font-dmSans text-body text-muted-foreground">
                            Deterministic preview of the proposed post-save
                            policy for this cycle and the next.
                        </p>
                    </div>
                    {validationIssues.length > 0 ? (
                        <span className="rounded-md border border-amber-700/30 bg-amber-50 px-3 py-2 font-dmSans text-caption font-semibold text-amber-900">
                            Showing last valid preview
                        </span>
                    ) : null}
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-2">
                    <PreviewCard
                        title="Current cycle"
                        railKeys={
                            previewPlans?.current.rails.map(
                                (rail) => rail.railKey,
                            ) ?? []
                        }
                        labels={labels}
                    />
                    <PreviewCard
                        title="Next cycle"
                        railKeys={
                            previewPlans?.next.rails.map(
                                (rail) => rail.railKey,
                            ) ?? []
                        }
                        labels={labels}
                    />
                </div>
            </section>

            <div className="flex flex-wrap items-center gap-3 rounded-md border border-copper/20 bg-surface-elevated p-4">
                <Button
                    type="button"
                    variant="roundedShimmer"
                    disabled={
                        isSaving ||
                        isLoading ||
                        requiresReload ||
                        !hasChanges ||
                        !validation?.success
                    }
                    onClick={() => void savePolicy()}
                >
                    {isSaving
                        ? "Saving…"
                        : `Save ${PLATFORM_LABELS[selectedPlatform]} policy`}
                </Button>
                <Button
                    type="button"
                    variant="outline"
                    disabled={isSaving || !hasChanges}
                    onClick={resetDraft}
                >
                    Reset unsaved changes
                </Button>
                <span className="font-dmSans text-caption text-muted-foreground">
                    {hasChanges ? "Unsaved changes" : "No unsaved changes"}
                </span>
            </div>
        </div>
    );
}

function PreviewCard({
    title,
    railKeys,
    labels,
}: {
    title: string;
    railKeys: DiscoveryRailKey[];
    labels: Map<DiscoveryRailKey, string>;
}) {
    return (
        <div className="rounded-md border border-copper/20 bg-surface-elevated p-4">
            <h3 className="font-urbanist-bold text-body text-foreground">
                {title}
            </h3>
            {railKeys.length > 0 ? (
                <ol className="mt-3 space-y-2 font-dmSans text-body text-foreground">
                    {railKeys.map((railKey, index) => (
                        <li key={railKey} className="flex items-center gap-3">
                            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-copper/15 text-caption font-semibold text-copper">
                                {index + 1}
                            </span>
                            {labels.get(railKey) ?? railKey}
                        </li>
                    ))}
                </ol>
            ) : (
                <p className="mt-3 font-dmSans text-caption text-muted-foreground">
                    No enabled rails in this preview.
                </p>
            )}
        </div>
    );
}
