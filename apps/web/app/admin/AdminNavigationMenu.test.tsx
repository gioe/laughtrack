/**
 * @vitest-environment happy-dom
 */

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import AdminNavigationMenu from "./AdminNavigationMenu";

afterEach(() => {
    cleanup();
});

describe("AdminNavigationMenu", () => {
    it("opens from the button and closes when the window is clicked", () => {
        render(<AdminNavigationMenu />);

        expect(screen.queryByRole("navigation")).toBeNull();

        fireEvent.click(
            screen.getByRole("button", { name: "Admin navigation" }),
        );

        expect(screen.getByRole("navigation")).toBeTruthy();
        expect(
            screen.getByRole("link", { name: /Podcasts/ }).getAttribute("href"),
        ).toBe("/admin/podcasts");

        fireEvent.pointerDown(document.body);

        expect(screen.queryByRole("navigation")).toBeNull();
    });
});
