"use client";

import { Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/ui/components/ui/button";

export type AdminDenyListEntry = {
    name: string;
    reason: string;
    addedBy: string;
    addedAt: string;
};

type Status = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

type Props = {
    entries: AdminDenyListEntry[];
};

function formatAddedAt(iso: string) {
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

export default function AdminDenyListManager({ entries }: Props) {
    const router = useRouter();
    const [name, setName] = useState("");
    const [reason, setReason] = useState("");
    const [removeReasons, setRemoveReasons] = useState<Record<string, string>>(
        {},
    );
    const [status, setStatus] = useState<Status>({ kind: "idle" });
    const [pendingName, setPendingName] = useState<string | null>(null);
    const [isPending, startTransition] = useTransition();

    async function submitAdd(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setStatus({ kind: "idle" });
        setPendingName(name.trim());

        let res: Response;
        try {
            res = await fetch("/api/admin/deny-list", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, reason }),
            });
        } catch (err) {
            setPendingName(null);
            setStatus({
                kind: "error",
                message: err instanceof Error ? err.message : "Network error",
            });
            return;
        }

        setPendingName(null);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            setStatus({
                kind: "error",
                message: body.error ?? `Request failed (${res.status})`,
            });
            return;
        }

        setName("");
        setReason("");
        setStatus({ kind: "ok", message: "Entry saved." });
        startTransition(() => router.refresh());
    }

    async function removeEntry(entryName: string) {
        const removeReason = removeReasons[entryName]?.trim() ?? "";
        setStatus({ kind: "idle" });
        setPendingName(entryName);

        let res: Response;
        try {
            res = await fetch("/api/admin/deny-list", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: entryName, reason: removeReason }),
            });
        } catch (err) {
            setPendingName(null);
            setStatus({
                kind: "error",
                message: err instanceof Error ? err.message : "Network error",
            });
            return;
        }

        setPendingName(null);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            setStatus({
                kind: "error",
                message: body.error ?? `Request failed (${res.status})`,
            });
            return;
        }

        setRemoveReasons((prev) => {
            const next = { ...prev };
            delete next[entryName];
            return next;
        });
        setStatus({ kind: "ok", message: "Entry removed." });
        startTransition(() => router.refresh());
    }

    return (
        <div className="space-y-6">
            <form
                onSubmit={submitAdd}
                className="grid gap-3 border border-gray-300 rounded-md p-4"
            >
                <div className="grid gap-3 md:grid-cols-[minmax(0,240px)_1fr_auto]">
                    <label className="grid gap-1 text-sm font-medium">
                        Name
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-copper focus:border-copper"
                            maxLength={255}
                            required
                        />
                    </label>
                    <label className="grid gap-1 text-sm font-medium">
                        Reason
                        <input
                            type="text"
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-copper focus:border-copper"
                            maxLength={1000}
                            required
                        />
                    </label>
                    <Button
                        type="submit"
                        variant="roundedShimmer"
                        className="self-end gap-2"
                        disabled={isPending || pendingName !== null}
                    >
                        <Plus className="h-4 w-4" aria-hidden="true" />
                        Add
                    </Button>
                </div>
                {status.kind === "ok" && (
                    <p className="text-sm text-green-700">{status.message}</p>
                )}
                {status.kind === "error" && (
                    <p className="text-sm text-red-700">{status.message}</p>
                )}
            </form>

            <ul className="divide-y divide-gray-300">
                {entries.map((entry) => (
                    <li
                        key={entry.name}
                        className="grid gap-3 py-4 lg:grid-cols-[minmax(0,1fr)_minmax(260px,360px)]"
                    >
                        <div className="min-w-0">
                            <div className="font-semibold text-gray-950">
                                {entry.name}
                            </div>
                            <div className="mt-1 text-sm text-gray-800">
                                {entry.reason}
                            </div>
                            <div className="mt-2 text-xs text-gray-600">
                                {entry.addedBy} ·{" "}
                                <time dateTime={entry.addedAt}>
                                    {formatAddedAt(entry.addedAt)}
                                </time>
                            </div>
                        </div>
                        <div className="flex items-end gap-2">
                            <label className="grid flex-1 gap-1 text-sm font-medium">
                                Removal reason
                                <input
                                    type="text"
                                    value={removeReasons[entry.name] ?? ""}
                                    onChange={(e) =>
                                        setRemoveReasons((prev) => ({
                                            ...prev,
                                            [entry.name]: e.target.value,
                                        }))
                                    }
                                    className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-copper focus:border-copper"
                                    maxLength={1000}
                                />
                            </label>
                            <Button
                                type="button"
                                variant="outline"
                                size="icon"
                                className="shrink-0"
                                onClick={() => void removeEntry(entry.name)}
                                disabled={
                                    pendingName !== null ||
                                    !removeReasons[entry.name]?.trim()
                                }
                                title="Remove entry"
                                aria-label={`Remove ${entry.name}`}
                            >
                                <Trash2
                                    className="h-4 w-4"
                                    aria-hidden="true"
                                />
                            </Button>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}
