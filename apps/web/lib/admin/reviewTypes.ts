export const reviewWorkflows = [
    "comedian_identity",
    "podcast_association",
    "event_eligibility",
] as const;
export type ReviewWorkflow = (typeof reviewWorkflows)[number];
export type ReviewStatus =
    | "pending"
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
    | "all";
export type ReviewAction = "approve" | "link" | "reject" | "defer";
export type ReviewResult = {
    decisionId?: string;
    status?: string;
    notice?: string;
};
export type ReviewEvidence = {
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
    targetId?: number;
    showIds?: number[];
    reason: string;
};
export const workflowLabels: Record<ReviewWorkflow, string> = {
    comedian_identity: "Comedian identity",
    podcast_association: "Podcast relationship",
    event_eligibility: "Event eligibility",
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
        sourceFilters: boolean;
    }
> = {
    comedian_identity: {
        statuses: [
            { value: "pending", label: "Needs review" },
            { value: "accepted", label: "Approved" },
            { value: "rejected", label: "Rejected" },
        ],
        defaultStatus: "pending",
        actions: [
            { value: "approve", label: "Approve new" },
            { value: "link", label: "Link existing" },
            { value: "reject", label: "Reject" },
        ],
        identityFields: true,
        reasonRequired: false,
        queued: false,
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
