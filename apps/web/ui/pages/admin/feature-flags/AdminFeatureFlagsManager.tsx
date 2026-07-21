"use client";

import { useState } from "react";
import type { YouTubeWebSubSettingsView } from "@/lib/admin/youtubeWebSub";
import { adminRequest } from "../shared/adminRequest";

type SettingsFlag = keyof YouTubeWebSubSettingsView;

type AdminFeatureFlagsManagerProps = {
    settings: YouTubeWebSubSettingsView;
};

export default function AdminFeatureFlagsManager({
    settings,
}: AdminFeatureFlagsManagerProps) {
    const [values, setValues] = useState<YouTubeWebSubSettingsView>(settings);
    const [savingFlag, setSavingFlag] = useState<SettingsFlag | null>(null);
    const [error, setError] = useState<string | null>(null);

    async function saveFlag(flag: SettingsFlag, value: boolean) {
        setSavingFlag(flag);
        setError(null);
        try {
            await adminRequest(
                "/api/admin/youtube-websub",
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ [flag]: value }),
                },
                {
                    httpErrorMessage: "Save failed",
                    networkErrorMessage: "Save failed",
                },
            );
            setValues((prev) => ({ ...prev, [flag]: value }));
        } catch (error) {
            setError(error instanceof Error ? error.message : "Save failed");
        } finally {
            setSavingFlag(null);
        }
    }

    return (
        <section className="rounded-md border border-copper/20 bg-surface-elevated p-5">
            <h2 className="font-urbanist-bold text-h3 text-foreground">
                Feature flags
            </h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <CheckboxField
                    label="Feed ingestion enabled"
                    checked={values.feedIngestionEnabled}
                    saving={savingFlag === "feedIngestionEnabled"}
                    onChange={(checked) =>
                        saveFlag("feedIngestionEnabled", checked)
                    }
                />
                <CheckboxField
                    label="Push delivery enabled"
                    checked={values.pushDeliveryEnabled}
                    saving={savingFlag === "pushDeliveryEnabled"}
                    onChange={(checked) =>
                        saveFlag("pushDeliveryEnabled", checked)
                    }
                />
            </div>
            {error ? (
                <p className="mt-3 font-dmSans text-caption text-red-700">
                    {error}
                </p>
            ) : null}
        </section>
    );
}

function CheckboxField({
    label,
    checked,
    saving,
    onChange,
}: {
    label: string;
    checked: boolean;
    saving: boolean;
    onChange: (checked: boolean) => void;
}) {
    return (
        <label className="flex items-center gap-2 font-dmSans text-body text-foreground">
            <input
                type="checkbox"
                aria-label={label}
                checked={checked}
                disabled={saving}
                onChange={(event) => onChange(event.target.checked)}
                className="h-4 w-4 rounded border-strong text-copper-dark focus:ring-copper/30"
            />
            <span className="font-semibold">{label}</span>
            {saving ? (
                <span className="text-caption text-muted-foreground">
                    Saving…
                </span>
            ) : null}
        </label>
    );
}
