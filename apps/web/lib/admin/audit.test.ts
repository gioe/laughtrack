import { describe, expect, it, vi } from "vitest";
import { writeAdminActionAudit } from "./audit";

describe("writeAdminActionAudit", () => {
    it("writes admin action audit rows through the provided transaction client", async () => {
        const create = vi.fn().mockResolvedValue({ id: 123 });
        const tx = {
            adminActionAudit: { create },
        };

        await writeAdminActionAudit(
            tx as unknown as Parameters<typeof writeAdminActionAudit>[0],
            {
                actorProfileId: "profile-1",
                action: "club.update",
                entityType: "club",
                entityId: 42,
                reason: "refresh venue metadata",
                before: { description: "old" },
                after: { description: "new" },
            },
        );

        expect(create).toHaveBeenCalledWith({
            data: {
                actorProfileId: "profile-1",
                action: "club.update",
                entityType: "club",
                entityId: "42",
                reason: "refresh venue metadata",
                before: { description: "old" },
                after: { description: "new" },
            },
        });
    });
});
