"use client";
import { useEffect, useState } from "react";
import type { InboxSummary } from "@/lib/admin/curation/inboxTypes";
import { button, field, inboxRequest } from "./inboxClient";
function Endpoint({
    kind,
    label,
    onSelect,
    disabled,
}: {
    kind: "comedian" | "podcast";
    label: string;
    onSelect: (x: InboxSummary | null) => void;
    disabled: boolean;
}) {
    const [q, setQ] = useState(""),
        [items, setItems] = useState<InboxSummary[]>([]),
        [chosen, setChosen] = useState<InboxSummary | null>(null),
        [error, setError] = useState("");
    useEffect(() => {
        const controller = new AbortController();
        if (!q.trim() || chosen) {
            setItems([]);
            return;
        }
        const timer = setTimeout(() => {
            inboxRequest<{ items: InboxSummary[] }>(
                `/api/admin/curation/inbox?${new URLSearchParams({ lookup: kind, q })}`,
                undefined,
                controller.signal,
            )
                .then((x) => {
                    if (!controller.signal.aborted) setItems(x.items);
                })
                .catch((e) => {
                    if (!controller.signal.aborted) setError(e.message);
                });
        }, 200);
        return () => {
            controller.abort();
            clearTimeout(timer);
        };
    }, [q, kind, chosen]);
    return (
        <div>
            <label>
                {label}
                <input
                    className={field}
                    type="search"
                    value={q}
                    disabled={disabled}
                    onChange={(e) => {
                        setQ(e.target.value);
                        setChosen(null);
                        onSelect(null);
                    }}
                />
            </label>
            {error && <p role="alert">{error}</p>}
            {chosen && (
                <p>
                    {chosen.label} · ID {chosen.recordId} · {chosen.state}
                </p>
            )}
            <ul>
                {items.map((x) => (
                    <li key={x.target.id}>
                        <button
                            disabled={disabled}
                            className={button}
                            onClick={() => {
                                setChosen(x);
                                setQ(x.label);
                                onSelect(x);
                            }}
                        >
                            {x.label} · ID {x.recordId} · {x.state}
                        </button>
                    </li>
                ))}
            </ul>
        </div>
    );
}
export function RelationshipProposal({
    onCreated,
    disabled,
}: {
    onCreated: (id: string) => void;
    disabled: boolean;
}) {
    const [role, setRole] = useState("alias_of"),
        [from, setFrom] = useState<InboxSummary | null>(null),
        [to, setTo] = useState<InboxSummary | null>(null),
        [url, setUrl] = useState(""),
        [explanation, setExplanation] = useState(""),
        [reason, setReason] = useState(""),
        [busy, setBusy] = useState(false),
        [error, setError] = useState("");
    async function propose() {
        if (!from?.recordId || !to?.recordId) return;
        setBusy(true);
        setError("");
        try {
            const result =
                role === "alias_of"
                    ? await inboxRequest<{ relationshipId: string }>(
                          "/api/admin/curation/parents",
                          {
                              operation: "propose",
                              childId: from.recordId,
                              parentId: to.recordId,
                              reason,
                              evidence: {
                                  samePerformer: true,
                                  sourceUrl: url,
                                  explanation,
                              },
                          },
                      )
                    : await inboxRequest<{ relationshipId: string }>(
                          "/api/admin/curation/hosts",
                          {
                              operation: "propose",
                              input: {
                                  comedianId: from.recordId,
                                  podcastId: to.recordId,
                                  role: role === "host_of" ? "host" : "cohost",
                                  source: "admin-review",
                                  sourceKey: url,
                                  evidence: { sourceUrl: url, explanation },
                                  reason,
                              },
                          },
                      );
            onCreated(result.relationshipId);
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setBusy(false);
        }
    }
    return (
        <fieldset
            disabled={disabled || busy}
            className="space-y-3 rounded-lg border border-strong bg-surface p-4"
        >
            <legend className="font-bold">Propose a relationship</legend>
            <label>
                Relationship role
                <select
                    className={field}
                    value={role}
                    onChange={(e) => {
                        setRole(e.target.value);
                        setTo(null);
                    }}
                >
                    <option value="alias_of">
                        Child → canonical parent (same performer)
                    </option>
                    <option value="host_of">Comedian → podcast host</option>
                    <option value="cohost_of">Comedian → podcast cohost</option>
                </select>
            </label>
            <Endpoint
                kind="comedian"
                label={role === "alias_of" ? "Child comedian" : "Comedian"}
                disabled={disabled || busy}
                onSelect={setFrom}
            />
            <Endpoint
                key={role}
                kind={role === "alias_of" ? "comedian" : "podcast"}
                label={role === "alias_of" ? "Canonical parent" : "Podcast"}
                disabled={disabled || busy}
                onSelect={setTo}
            />
            <label className="block">
                Evidence URL
                <input
                    className={field}
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                />
            </label>
            <label className="block">
                {role === "alias_of"
                    ? "Why both names identify the same performer"
                    : "Evidence of this hosting role"}
                <textarea
                    className={field}
                    minLength={20}
                    maxLength={2000}
                    value={explanation}
                    onChange={(e) => setExplanation(e.target.value)}
                />
            </label>
            <label className="block">
                Proposal reason
                <input
                    className={field}
                    maxLength={2000}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                />
            </label>
            <p>
                Saving evidence does not establish the relationship. Review the
                pair next; its preview explains any existing parent replacement.
                Rejected pairs must first be restored.
            </p>
            {error && <p role="alert">{error}</p>}
            <button
                className={button}
                disabled={
                    !from ||
                    !to ||
                    !/^https?:\/\//.test(url) ||
                    explanation.trim().length < 20 ||
                    !reason.trim() ||
                    disabled ||
                    busy
                }
                onClick={() => void propose()}
            >
                Save evidence and review pair
            </button>
        </fieldset>
    );
}
