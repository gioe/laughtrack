"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/ui/components/ui/button";
import { adminRequest } from "../shared/adminRequest";

interface Props {
    clubId: number;
    clubName: string;
    initialDescription: string;
}

export default function AdminClubEditor({
    clubId,
    clubName,
    initialDescription,
}: Props) {
    const router = useRouter();
    const [description, setDescription] = useState(initialDescription);
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
        };
        try {
            await adminRequest(
                `/api/admin/clubs/${clubId}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                },
                {
                    networkErrorMessage: (error) =>
                        error instanceof Error
                            ? error.message
                            : "Unknown network error",
                },
            );
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
