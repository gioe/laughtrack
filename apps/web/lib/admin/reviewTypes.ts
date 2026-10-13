export const reviewWorkflows = [
    "comedian_identity",
    "podcast_association",
] as const;
export type ReviewWorkflow = (typeof reviewWorkflows)[number];
export type ReviewStatus = "pending" | "accepted" | "rejected";
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
    evidence: ReviewEvidence[];
    matches: { id: number; name: string }[];
    history: {
        id: string;
        action: string;
        reason: string;
        actor: string;
        createdAt: string;
        undone: boolean;
    }[];
};
export type ReviewPage = { items: ReviewItem[]; total: number; page: number };
export type ReviewSubmission = {
    workflow: ReviewWorkflow;
    id: string;
    token: string;
    action: "approve" | "link" | "reject";
    name?: string;
    targetId?: number;
    showIds?: number[];
    reason: string;
};
export const workflowLabels: Record<ReviewWorkflow, string> = {
    comedian_identity: "Comedian identity",
    podcast_association: "Podcast relationship",
};
