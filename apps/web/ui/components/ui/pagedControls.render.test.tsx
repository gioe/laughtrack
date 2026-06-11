/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import PagedControls from "./pagedControls";

const { pushMock } = vi.hoisted(() => ({
    pushMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: pushMock }),
    usePathname: () => "/user/profile",
    useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("@/hooks/useMotionProps", () => ({
    useMotionProps: () => ({
        prefersReducedMotion: false,
    }),
}));

type ScrollIntoView = (arg?: boolean | ScrollIntoViewOptions) => void;

describe("PagedControls scroll opt-in", () => {
    let scrollSpy: ReturnType<typeof vi.fn<ScrollIntoView>>;

    beforeEach(() => {
        vi.clearAllMocks();
        scrollSpy = vi.fn<ScrollIntoView>();
        window.HTMLElement.prototype.scrollIntoView = scrollSpy;
    });

    afterEach(() => {
        cleanup();
    });

    it("stays in place when no scrollTargetRef is passed (profile sections)", () => {
        render(
            <PagedControls currentPage={1} totalPages={5} queryKey="page" />,
        );

        fireEvent.click(screen.getByRole("link", { name: "Go to page 2" }));

        expect(pushMock).toHaveBeenCalledWith("/user/profile?page=2", {
            scroll: false,
        });
        expect(scrollSpy).not.toHaveBeenCalled();
    });

    it("scrolls the provided target into view after navigating", () => {
        const Host = () => {
            const targetRef = React.useRef<HTMLDivElement>(null);
            return (
                <>
                    <div ref={targetRef}>Results top</div>
                    <PagedControls
                        currentPage={1}
                        totalPages={5}
                        queryKey="page"
                        scrollTargetRef={targetRef}
                    />
                </>
            );
        };
        render(<Host />);

        fireEvent.click(screen.getByRole("link", { name: "Go to page 2" }));

        expect(scrollSpy).toHaveBeenCalledWith({
            behavior: "smooth",
            block: "start",
        });
        const target = scrollSpy.mock.contexts[0] as HTMLElement;
        expect(target.textContent).toBe("Results top");
    });

    it("does not scroll on disabled navigation", () => {
        const Host = () => {
            const targetRef = React.useRef<HTMLDivElement>(null);
            return (
                <>
                    <div ref={targetRef}>Results top</div>
                    <PagedControls
                        currentPage={1}
                        totalPages={5}
                        queryKey="page"
                        scrollTargetRef={targetRef}
                    />
                </>
            );
        };
        render(<Host />);

        fireEvent.click(screen.getByRole("link", { name: /previous/i }));

        expect(pushMock).not.toHaveBeenCalled();
        expect(scrollSpy).not.toHaveBeenCalled();
    });
});
