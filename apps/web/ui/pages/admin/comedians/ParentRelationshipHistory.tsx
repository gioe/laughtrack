"use client";
import { useEffect, useState } from "react";
import { adminRequest } from "../shared/adminRequest";
import { Button } from "@/ui/components/ui/button";
type Edge = {
    id: string;
    parent_name: string;
    child_name: string;
    disposition: string;
    version: number;
    decisions: { id: string; action: string; actor: string; reason: string }[];
    observations: {
        id: string;
        source?: string;
        evidence: {
            sourceUrl?: string;
            explanation?: string;
            reason?: string;
            actor?: string;
        };
    }[];
};
export function ParentRelationshipHistory({
    childId,
    reason,
    refreshKey,
}: {
    childId: number;
    reason: string;
    refreshKey: number;
}) {
    const [edges, setEdges] = useState<Edge[]>([]),
        [error, setError] = useState(""),
        [refresh, setRefresh] = useState(0),
        [busy, setBusy] = useState(false);
    const [preview, setPreview] = useState<{
        command: Record<string, unknown>;
        effects: string[];
    } | null>(null);
    useEffect(() => {
        let active = true;
        adminRequest<{ relationships: Edge[] }>(
            `/api/admin/curation/parents?childId=${childId}`,
        )
            .then((data) => {
                if (active) {
                    setEdges(data.relationships ?? []);
                    setError("");
                }
            })
            .catch((e) => {
                if (active) setError(e.message);
            });
        return () => {
            active = false;
        };
    }, [childId, refreshKey, refresh]);
    async function decide(edge: Edge, action: string) {
        if (!reason.trim()) {
            setError("Enter a relationship reason before deciding.");
            return;
        }
        setBusy(true);
        setError("");
        try {
            const command = {
                requestId: crypto.randomUUID(),
                target: { type: "relationship", kind: "alias_of", id: edge.id },
                expectedVersion: edge.version,
                action,
                reason: reason.trim(),
            };
            const data = await adminRequest<{ effects: string[] }>(
                "/api/admin/curation",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ operation: "preview", command }),
                },
            );
            setPreview({ command, effects: data.effects });
        } catch (e) {
            setError(e instanceof Error ? e.message : "Preview failed");
        } finally {
            setBusy(false);
        }
    }
    async function apply() {
        if (!preview) return;
        setBusy(true);
        try {
            const result = await adminRequest<{
                status: string;
                error?: string;
            }>("/api/admin/curation", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    operation: "submit",
                    command: preview.command,
                }),
            });
            if (result.status !== "applied")
                throw Error(result.error ?? "Decision did not apply");
            setPreview(null);
            setRefresh((v) => v + 1);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Decision failed");
        } finally {
            setBusy(false);
        }
    }
    return (
        <details className="rounded border border-subtle p-2">
            <summary>Relationship history ({edges.length})</summary>
            {error && <p role="alert">{error}</p>}
            {edges.map((edge) => (
                <div
                    key={edge.id}
                    className="space-y-2 border-t border-subtle py-2"
                >
                    <p>
                        {edge.child_name} → {edge.parent_name}:{" "}
                        {edge.disposition}
                    </p>
                    {edge.observations.map((o) => (
                        <p key={o.id}>
                            {o.evidence.explanation ??
                                o.evidence.reason ??
                                o.source}{" "}
                            {o.evidence.sourceUrl &&
                                /^https?:/.test(o.evidence.sourceUrl) && (
                                    <a
                                        href={o.evidence.sourceUrl}
                                        target="_blank"
                                        rel="noreferrer"
                                    >
                                        Evidence
                                    </a>
                                )}
                        </p>
                    ))}
                    <ul>
                        {edge.decisions.map((d) => (
                            <li key={d.id}>
                                {d.action}: {d.reason} — {d.actor}
                            </li>
                        ))}
                    </ul>
                    {edge.disposition === "proposed" && (
                        <Button
                            variant="outline"
                            disabled={busy}
                            onClick={() => void decide(edge, "reject")}
                        >
                            Reject proposal
                        </Button>
                    )}
                    {["rejected", "severed"].includes(edge.disposition) && (
                        <Button
                            variant="outline"
                            disabled={busy}
                            onClick={() => void decide(edge, "restore")}
                        >
                            Restore for review
                        </Button>
                    )}
                </div>
            ))}
            {preview && (
                <div role="status">
                    <ul>
                        {preview.effects.map((e) => (
                            <li key={e}>{e}</li>
                        ))}
                    </ul>
                    <Button disabled={busy} onClick={() => void apply()}>
                        Apply history decision
                    </Button>
                    <Button variant="outline" onClick={() => setPreview(null)}>
                        Cancel
                    </Button>
                </div>
            )}
        </details>
    );
}
