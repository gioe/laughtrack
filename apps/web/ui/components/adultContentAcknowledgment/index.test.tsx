/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
    render,
    screen,
    waitFor,
    fireEvent,
    cleanup,
} from "@testing-library/react";
import AdultContentAcknowledgment from "./index";

const STORAGE_KEY = "laughtrack.adult-content-acknowledged";

describe("AdultContentAcknowledgment", () => {
    beforeEach(() => {
        window.localStorage.clear();
        document.cookie =
            "laughtrack_adult_content_acknowledged=;path=/;max-age=0";
    });

    afterEach(() => {
        cleanup();
    });

    it("shows the acknowledgment for a fresh browser state", async () => {
        render(<AdultContentAcknowledgment />);

        expect(
            await screen.findByRole("dialog", {
                name: "Adult content notice",
            }),
        ).toBeTruthy();
        expect(
            screen.getByText(/This app shows live comedy events/i),
        ).toBeTruthy();
    });

    it("persists acknowledgment and hides after confirmation", async () => {
        render(<AdultContentAcknowledgment />);

        const button = await screen.findByRole("button", {
            name: "I understand",
        });
        fireEvent.click(button);

        await waitFor(() => {
            expect(screen.queryByRole("dialog")).toBeNull();
        });
        expect(window.localStorage.getItem(STORAGE_KEY)).toBe("true");
        expect(document.cookie).toContain(
            "laughtrack_adult_content_acknowledged=true",
        );
    });

    it("does not reappear when acknowledgment is already stored", async () => {
        window.localStorage.setItem(STORAGE_KEY, "true");

        render(<AdultContentAcknowledgment />);

        await waitFor(() => {
            expect(screen.queryByRole("dialog")).toBeNull();
        });
    });
});
