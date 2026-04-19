"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/ui/components/ui/button";

const DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
] as const;

type Day = (typeof DAYS)[number];
type HoursState = Record<Day, string>;

interface Props {
    clubId: number;
    clubName: string;
    initialDescription: string;
    initialHours: Record<string, unknown> | null;
}

function coerceInitialHours(src: Record<string, unknown> | null): HoursState {
    const out = Object.fromEntries(DAYS.map((d) => [d, ""])) as HoursState;
    if (!src) return out;
    for (const key of Object.keys(src)) {
        const day = key.toLowerCase() as Day;
        if ((DAYS as readonly string[]).includes(day)) {
            const val = src[key];
            if (typeof val === "string") out[day] = val;
        }
    }
    return out;
}

export default function AdminClubEditor({
    clubId,
    clubName,
    initialDescription,
    initialHours,
}: Props) {
    const router = useRouter();
    const [description, setDescription] = useState(initialDescription);
    const [hours, setHours] = useState<HoursState>(
        coerceInitialHours(initialHours),
    );
    const [isPending, startTransition] = useTransition();
    const [status, setStatus] = useState<{
        kind: "idle" | "ok" | "error";
        message?: string;
    }>({ kind: "idle" });

    async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setStatus({ kind: "idle" });
        const payload = {
            description: description.trim() === "" ? null : description,
            hours: Object.fromEntries(DAYS.map((d) => [d, hours[d]])),
        };
        try {
            const res = await fetch(`/api/admin/clubs/${clubId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                setStatus({
                    kind: "error",
                    message: body.error ?? `Request failed (${res.status})`,
                });
                return;
            }
            setStatus({ kind: "ok", message: "Saved." });
            startTransition(() => router.refresh());
        } catch (err) {
            setStatus({
                kind: "error",
                message:
                    err instanceof Error
                        ? err.message
                        : "Unknown network error",
            });
        }
    }

    return (
        <form onSubmit={onSubmit} className="space-y-6">
            <section>
                <label
                    className="block font-semibold mb-2"
                    htmlFor="description"
                >
                    Description
                </label>
                <textarea
                    id="description"
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-copper focus:border-copper"
                    rows={6}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    maxLength={5000}
                />
                <div className="text-xs text-gray-600 mt-1">
                    {description.length} / 5000
                </div>
            </section>

            <section>
                <h2 className="font-semibold mb-2">Hours</h2>
                <div className="space-y-2">
                    {DAYS.map((day) => (
                        <div
                            key={day}
                            className="grid grid-cols-[120px_1fr] items-center gap-3"
                        >
                            <label
                                htmlFor={`hours-${day}`}
                                className="capitalize"
                            >
                                {day}
                            </label>
                            <input
                                id={`hours-${day}`}
                                type="text"
                                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-copper focus:border-copper"
                                placeholder="e.g. 7:00 PM – 11:00 PM, or Closed"
                                value={hours[day]}
                                onChange={(e) =>
                                    setHours((prev) => ({
                                        ...prev,
                                        [day]: e.target.value,
                                    }))
                                }
                                maxLength={64}
                            />
                        </div>
                    ))}
                </div>
                <p className="text-xs text-gray-600 mt-2">
                    Leave all days blank to clear hours entirely.
                </p>
            </section>

            <div className="flex items-center gap-3">
                <Button
                    type="submit"
                    variant="roundedShimmer"
                    disabled={isPending}
                >
                    Save
                </Button>
                <Link
                    href={`/club/${encodeURIComponent(clubName)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-100 transition-colors"
                >
                    View public page
                </Link>
                {status.kind === "ok" && (
                    <span className="text-green-600 text-sm">
                        {status.message}
                    </span>
                )}
                {status.kind === "error" && (
                    <span className="text-red-600 text-sm">
                        {status.message}
                    </span>
                )}
            </div>
        </form>
    );
}
