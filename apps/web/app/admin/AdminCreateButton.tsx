"use client";

import { Button } from "@/ui/components/ui/button";
import { Plus, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

type EntityKind = "comedian" | "club";

type Status = {
    kind: "idle" | "error";
    message?: string;
};

const CREATE_BUTTON_LABEL = "Create item";

function entityFromPath(pathname: string): EntityKind | null {
    if (pathname.startsWith("/admin/comedians")) return "comedian";
    if (pathname.startsWith("/admin/clubs")) return "club";
    return null;
}

function fieldClassName() {
    return "rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30";
}

export default function AdminCreateButton() {
    const pathname = usePathname();
    const router = useRouter();
    const entity = useMemo(() => entityFromPath(pathname), [pathname]);
    const [isOpen, setIsOpen] = useState(false);
    const [status, setStatus] = useState<Status>({ kind: "idle" });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [comedianName, setComedianName] = useState("");
    const [clubName, setClubName] = useState("");
    const [clubAddress, setClubAddress] = useState("");
    const [clubWebsite, setClubWebsite] = useState("");

    const title =
        entity === "comedian"
            ? "Create comedian"
            : entity === "club"
              ? "Create club"
              : "Create item";

    function closeModal() {
        if (isSubmitting) return;
        setIsOpen(false);
        setStatus({ kind: "idle" });
    }

    async function submitComedian() {
        return fetch("/api/admin/comedians", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: comedianName.trim() }),
        });
    }

    async function submitClub() {
        return fetch("/api/admin/clubs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: clubName.trim(),
                address: clubAddress.trim(),
                website: clubWebsite.trim(),
            }),
        });
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!entity) return;

        setIsSubmitting(true);
        setStatus({ kind: "idle" });

        try {
            const response =
                entity === "comedian"
                    ? await submitComedian()
                    : await submitClub();
            const body = await response.json().catch(() => ({}));

            if (!response.ok) {
                setStatus({
                    kind: "error",
                    message:
                        typeof body.error === "string"
                            ? body.error
                            : "Create failed",
                });
                return;
            }

            setIsOpen(false);
            setComedianName("");
            setClubName("");
            setClubAddress("");
            setClubWebsite("");
            router.refresh();
        } catch {
            setStatus({
                kind: "error",
                message: "Create failed",
            });
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <>
            <Button
                type="button"
                size="icon"
                aria-label={CREATE_BUTTON_LABEL}
                className="fixed bottom-6 right-6 z-40 h-14 w-14 rounded-full bg-copper-dark text-white shadow-xl hover:bg-cedar focus-visible:ring-2 focus-visible:ring-copper/40"
                onClick={() => setIsOpen(true)}
            >
                <Plus className="h-6 w-6" />
            </Button>

            {isOpen ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4 backdrop-blur-sm">
                    <div
                        role="dialog"
                        aria-modal="true"
                        aria-label={title}
                        className="w-full max-w-lg rounded-md border border-copper/25 bg-coconut-cream p-5 shadow-2xl outline-none"
                    >
                        <div className="mb-4 flex items-center justify-between gap-3">
                            <h2 className="font-gilroy-bold text-h2 text-cedar">
                                {title}
                            </h2>
                            <button
                                type="button"
                                aria-label="Close dialog"
                                className="rounded-md p-2 text-soft-charcoal hover:bg-copper/10 hover:text-cedar focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-copper/40"
                                onClick={closeModal}
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        {entity ? (
                            <form
                                className="grid gap-4"
                                onSubmit={handleSubmit}
                            >
                                {entity === "comedian" ? (
                                    <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                        Name
                                        <input
                                            required
                                            value={comedianName}
                                            onChange={(event) =>
                                                setComedianName(
                                                    event.target.value,
                                                )
                                            }
                                            className={fieldClassName()}
                                        />
                                    </label>
                                ) : (
                                    <>
                                        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                            Name
                                            <input
                                                required
                                                value={clubName}
                                                onChange={(event) =>
                                                    setClubName(
                                                        event.target.value,
                                                    )
                                                }
                                                className={fieldClassName()}
                                            />
                                        </label>
                                        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                            Address
                                            <input
                                                required
                                                value={clubAddress}
                                                onChange={(event) =>
                                                    setClubAddress(
                                                        event.target.value,
                                                    )
                                                }
                                                className={fieldClassName()}
                                            />
                                        </label>
                                        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                            Website
                                            <input
                                                required
                                                type="url"
                                                value={clubWebsite}
                                                onChange={(event) =>
                                                    setClubWebsite(
                                                        event.target.value,
                                                    )
                                                }
                                                className={fieldClassName()}
                                            />
                                        </label>
                                    </>
                                )}

                                {status.kind === "error" ? (
                                    <p className="rounded-md border border-red-700/30 bg-red-50 px-3 py-2 font-dmSans text-body font-semibold text-red-900">
                                        {status.message}
                                    </p>
                                ) : null}

                                <div className="flex justify-end gap-2">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="border-copper/40 bg-white text-cedar hover:bg-copper/10"
                                        disabled={isSubmitting}
                                        onClick={closeModal}
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        type="submit"
                                        className="bg-copper-dark text-white hover:bg-cedar"
                                        disabled={isSubmitting}
                                    >
                                        {isSubmitting ? "Creating" : title}
                                    </Button>
                                </div>
                            </form>
                        ) : (
                            <div className="grid gap-4">
                                <p className="font-dmSans text-body text-soft-charcoal">
                                    Creation is available for Comedians and
                                    Clubs.
                                </p>
                                <div className="flex justify-end">
                                    <Button
                                        type="button"
                                        className="bg-copper-dark text-white hover:bg-cedar"
                                        onClick={closeModal}
                                    >
                                        Close
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ) : null}
        </>
    );
}
