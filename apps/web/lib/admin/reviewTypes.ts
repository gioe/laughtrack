export const reviewWorkflows = [
    "comedian_identity",
    "podcast_association",
    "event_eligibility",
    "comedian_visibility",
    "club_visibility",
] as const;
export type ReviewWorkflow = (typeof reviewWorkflows)[number];
export type ReviewStatus =
    | "pending"
    | "resolved"
    | "accepted"
    | "rejected"
    | "review"
    | "accept"
    | "reject"
    | "approve"
    | "defer"
    | "stale_review"
    | "stale_policy"
    | "awaiting_observation"
    | "all"
    | "active"
    | "blocked";
export type ReviewAction =
    | "approve"
    | "revoke_billing"
    | "resolve_multiple"
    | "link"
    | "reject"
    | "defer"
    | "block"
    | "unblock";
export type ReviewResult = {
    decisionId?: string;
    status?: string;
    notice?: string;
    revalidateTags?: string[];
};
export type ReviewEvidence = {
    rawName?: string;
    clubId?: number;
    id: string;
    title: string;
    context: string;
    url: string | null;
    source: string;
    kind: string;
    showId?: number;
    date?: string;
};
export type ReviewItem = {
    id: string;
    workflow: ReviewWorkflow;
    title: string;
    subtitle: string;
    status: ReviewStatus;
    token: string;
    actions?: ReviewAction[];
    notice?: string;
    processing?: boolean;
    billings?: {
        venue: string;
        id: string;
        source: string;
        rawName: string;
        members: string[];
    }[];
    evidence: ReviewEvidence[];
    matches: { id: number; name: string }[];
    history: {
        id: string;
        action: string;
        reason: string;
        actor: string;
        createdAt: string;
        undone: boolean;
        status?: string;
    }[];
};
export type ReviewPage = {
    items: ReviewItem[];
    total: number | null;
    page: number;
    cursor?: { ceiling: number; next: number | null };
};
export type ReviewSubmission = {
    workflow: ReviewWorkflow;
    id: string;
    token: string;
    action: ReviewAction;
    requestId?: string;
    name?: string;
    targetIds?: number[];
    evidenceId?: string;
    billingId?: string;
    targetId?: number;
    showIds?: number[];
    reason: string;
};
export const workflowLabels: Record<ReviewWorkflow, string> = {
    comedian_identity: "Comedian identity",
    podcast_association: "Podcast relationship",
    event_eligibility: "Event eligibility",
    comedian_visibility: "Comedian visibility",
    club_visibility: "Club visibility",
};

// Each adapter supplies the same item/evidence/history shape. Capabilities keep
// the shell independent of entity-specific states and publication semantics.
export const reviewDefinitions: Record<
    ReviewWorkflow,
    {
        statuses: { value: ReviewStatus; label: string }[];
        defaultStatus: ReviewStatus;
        actions: { value: ReviewAction; label: string }[];
        identityFields: boolean;
        reasonRequired: boolean;
        queued: boolean;
        confirmationRequired?: boolean;
        confirmationNotice?: string;
        sourceFilters: boolean;
    }
> = {
    comedian_visibility: {
        statuses: [
            { value: "all", label: "All records" },
            { value: "active", label: "Shown publicly" },
            { value: "blocked", label: "Hidden publicly" },
        ],
        defaultStatus: "all",
        actions: [
            { value: "block", label: "Hide publicly" },
            { value: "unblock", label: "Show publicly" },
        ],
        identityFields: false,
        reasonRequired: true,
        queued: false,
        sourceFilters: false,
        confirmationRequired: true,
        confirmationNotice:
            "This changes public visibility immediately. You can review the record again to reverse it.",
    },
    club_visibility: {
        statuses: [
            { value: "all", label: "All records" },
            { value: "active", label: "Shown publicly" },
            { value: "blocked", label: "Hidden publicly" },
        ],
        defaultStatus: "all",
        actions: [
            { value: "block", label: "Hide publicly" },
            { value: "unblock", label: "Show publicly" },
        ],
        identityFields: false,
        reasonRequired: true,
        queued: false,
        sourceFilters: false,
        confirmationRequired: true,
        confirmationNotice:
            "This changes public visibility immediately. You can review the record again to reverse it.",
    },
    comedian_identity: {
        statuses: [
            { value: "pending", label: "Needs review" },
            { value: "accepted", label: "Approved" },
            { value: "resolved", label: "Joint billing resolved" },
            { value: "rejected", label: "Rejected" },
        ],
        defaultStatus: "pending",
        actions: [
            { value: "approve", label: "Approve new" },
            { value: "link", label: "Link existing" },
            {
                value: "revoke_billing",
                label: "Stop reusing billing",
            },
            {
                value: "resolve_multiple",
                label: "Resolve to multiple performers",
            },
            { value: "reject", label: "Reject" },
        ],
        identityFields: true,
        reasonRequired: true,
        queued: false,
        confirmationRequired: true,
        confirmationNotice:
            "Approval validates this performer identity and only the selected appearances. Rejection blocks this candidate identity from future intake; it does not block unrelated names or shows.",
        sourceFilters: false,
    },
    podcast_association: {
        statuses: [
            { value: "pending", label: "Needs review" },
            { value: "accepted", label: "Approved" },
            { value: "rejected", label: "Rejected" },
        ],
        defaultStatus: "pending",
        actions: [
            { value: "approve", label: "Approve relationship" },
            { value: "reject", label: "Reject" },
        ],
        identityFields: false,
        reasonRequired: false,
        queued: false,
        sourceFilters: false,
    },
    event_eligibility: {
        statuses: [
            { value: "all", label: "All states" },
            { value: "review", label: "Needs review" },
            { value: "accept", label: "Automatically accepted" },
            { value: "approve", label: "Approved" },
            { value: "reject", label: "Rejected" },
            { value: "defer", label: "Deferred" },
            { value: "stale_review", label: "Evidence changed" },
            { value: "stale_policy", label: "Policy changed" },
            { value: "awaiting_observation", label: "Awaiting observation" },
        ],
        defaultStatus: "review",
        actions: [
            { value: "approve", label: "Approve event" },
            { value: "reject", label: "Reject" },
            { value: "defer", label: "Defer" },
        ],
        identityFields: false,
        reasonRequired: true,
        queued: true,
        sourceFilters: true,
    },
};
