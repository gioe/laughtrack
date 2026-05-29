import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        $queryRaw: vi.fn(),
    },
}));

import { GET } from "./route";
import { db } from "@/lib/db";

const mockQueryRaw = vi.mocked(db.$queryRaw);

beforeEach(() => {
    vi.clearAllMocks();
});

describe("GET /api/health", () => {
    it("returns 200 with status ok when the database is reachable", async () => {
        mockQueryRaw.mockResolvedValue([{ "?column?": 1 }] as never);

        const res = await GET();
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.status).toBe("ok");
        expect(body.database).toBe("ok");
        expect(res.headers.get("Cache-Control")).toBe("no-store, max-age=0");
        expect(mockQueryRaw).toHaveBeenCalledTimes(1);
    });

    it("returns 503 when the database query throws", async () => {
        mockQueryRaw.mockRejectedValue(new Error("Neon unreachable"));

        const res = await GET();
        const body = await res.json();

        expect(res.status).toBe(503);
        expect(body.status).toBe("error");
        expect(body.database).toBe("unreachable");
        expect(res.headers.get("Cache-Control")).toBe("no-store, max-age=0");
    });
});
