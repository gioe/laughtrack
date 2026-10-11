import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
vi.mock("@/auth", () => ({ auth: vi.fn() }));
vi.mock("@/lib/db", () => ({ db: { userProfile: { findFirst: vi.fn() } } }));
vi.mock("@/lib/metrics", () => ({ withRequestMetrics: (fn: unknown) => fn }));
vi.mock("@/lib/admin/eventReviews", async (importOriginal) => ({
    ...(await importOriginal<typeof import("@/lib/admin/eventReviews")>()),
    listEventReviews: vi.fn(),
    getEventReview: vi.fn(),
    submitEventReview: vi.fn(),
}));
import { auth } from "@/auth";
import { db } from "@/lib/db";
import {
    getEventReview,
    listEventReviews,
    submitEventReview,
} from "@/lib/admin/eventReviews";
import { GET, POST } from "./route";
const payload = {
    id: "10000000-0000-4000-8000-000000000001",
    candidateId: 1,
    token: "a".repeat(64),
    action: "approve",
    reason: "Billed stand-up",
};
const get = () => new NextRequest("http://localhost/api/admin/event-reviews");
const post = (body: unknown = payload) =>
    new NextRequest(get().url, { method: "POST", body: JSON.stringify(body) });
beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(auth).mockResolvedValue({
        profile: { id: "session-profile", userid: "u" },
    } as never);
    vi.mocked(db.userProfile.findFirst).mockResolvedValue({
        id: "server-profile",
        userid: "u",
        role: "admin",
    } as never);
});
it.each([401, 422, 403])(
    "denies unauthenticated/non-admin access %s on reads and writes",
    async (status) => {
        if (status === 401) vi.mocked(auth).mockResolvedValue(null as never);
        if (status === 422) vi.mocked(auth).mockResolvedValue({} as never);
        if (status === 403)
            vi.mocked(db.userProfile.findFirst).mockResolvedValue({
                id: "p",
                role: "user",
            } as never);
        expect((await GET(get())).status).toBe(status);
        expect((await POST(post())).status).toBe(status);
        expect(listEventReviews).not.toHaveBeenCalled();
        expect(submitEventReview).not.toHaveBeenCalled();
    },
);
it("derives the actor from the authenticated database profile", async () => {
    vi.mocked(submitEventReview).mockResolvedValue({
        status: "pending",
    } as never);
    expect((await POST(post())).status).toBe(202);
    expect(submitEventReview).toHaveBeenCalledWith(payload, "server-profile");
    expect((await POST(post({ ...payload, actor: "spoof" }))).status).toBe(400);
});
it("validates blank reasons, invalid IDs and malformed JSON", async () => {
    expect((await POST(post({ ...payload, reason: "  " }))).status).toBe(400);
    expect(
        (await POST(new NextRequest(get().url, { method: "POST", body: "{" })))
            .status,
    ).toBe(400);
    expect((await GET(new NextRequest(get().url + "?id=-1"))).status).toBe(400);
    vi.mocked(getEventReview).mockResolvedValue(null);
    expect((await GET(new NextRequest(get().url + "?id=2"))).status).toBe(404);
});
