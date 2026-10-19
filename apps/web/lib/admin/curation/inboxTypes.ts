import type { Command, Target } from "./decisions";
export type InboxSummary = {
    target: Target;
    label: string;
    state: string;
    version: number;
    recordId: number | null;
    sourceLabel?: string;
    targetLabel?: string;
    sourceRecordId?: number;
    targetRecordId?: number;
};
export type InboxDetail = InboxSummary & {
    keys: {
        namespace: string;
        scope: string;
        value: string;
        key_type: string;
    }[];
    observations: {
        id: string;
        source: string;
        source_key: string;
        evidence: Record<string, unknown>;
        recorded_at: string;
    }[];
    decisions: {
        id: string;
        action: string;
        actor: string;
        reason: string;
        created_at: string;
        before_state: string;
        after_state: string;
    }[];
    requests: {
        id: string;
        status: string;
        action: string;
        reason: string;
        actor: string;
        error: string | null;
    }[];
    matches: InboxSummary[];
    reconciliations: {
        id: string;
        resolved_at: string | null;
        actor: string | null;
        reason: string | null;
    }[];
    candidateId: string | null;
};
export type InboxPage = { items: InboxSummary[]; hasMore: boolean };
export type InboxPreview = {
    effects: string[];
    boundaries?: string;
    restoration?: string;
    available?: boolean;
    disabledReason?: string;
    previewToken?: string;
    token?: string;
    mode?: string;
};
export type InboxAction = Command["action"];
export function availableActions(item: InboxSummary): InboxAction[] {
    if (item.target.type === "entity")
        return item.state === "blocked"
            ? ["restore"]
            : item.state === "approved"
              ? ["block"]
              : item.target.scope === "entity" &&
                  item.target.kind !== "comedian"
                ? ["approve", "block"]
                : ["block"];
    return item.state === "proposed"
        ? ["confirm", "reject"]
        : item.state === "confirmed"
          ? ["sever"]
          : ["restore"];
}
export const actionLabels: Record<InboxAction, string> = {
    approve: "Approve intake",
    block: "Reject and block future intake",
    restore: "Restore for review",
    confirm: "Establish relationship",
    reject: "Reject relationship",
    sever: "Sever relationship",
};
