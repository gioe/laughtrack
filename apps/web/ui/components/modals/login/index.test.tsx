/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";
import React from "react";

// vi.hoisted ensures these are available before vi.mock factory hoisting runs
const { mockOnOpen, mockOnClose, mockReplace, mockRefresh, mockToastError } =
    vi.hoisted(() => ({
        mockOnOpen: vi.fn(),
        mockOnClose: vi.fn(),
        mockReplace: vi.fn(),
        mockRefresh: vi.fn(),
        mockToastError: vi.fn(),
    }));

let mockIsOpen = false;
let mockSearchParamsGet: (key: string) => string | null = () => null;

vi.mock("@/hooks", () => ({
    useLoginModal: (
        selector: (s: {
            isOpen: boolean;
            onOpen: () => void;
            onClose: () => void;
        }) => unknown,
    ) =>
        selector({
            isOpen: mockIsOpen,
            onOpen: mockOnOpen,
            onClose: mockOnClose,
        }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ replace: mockReplace, refresh: mockRefresh }),
    useSearchParams: () => ({ get: (key: string) => mockSearchParamsGet(key) }),
}));

vi.mock("react-hot-toast", () => ({ default: { error: mockToastError } }));

vi.mock("../fullscreen", () => ({
    default: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="modal">{children}</div>
    ),
}));

vi.mock("@/ui/pages/login", () => ({
    default: () => <div data-testid="login-form" />,
}));

import LoginModal from "./index";

beforeEach(() => {
    vi.clearAllMocks();
    mockIsOpen = false;
    mockSearchParamsGet = () => null;
    Object.defineProperty(window, "location", {
        value: {
            href: "https://laugh-track.com/",
            origin: "https://laugh-track.com",
        },
        writable: true,
        configurable: true,
    });
});

describe("LoginModal", () => {
    it("does not show a toast when there is no error param", () => {
        mockSearchParamsGet = () => null;

        act(() => {
            render(<LoginModal />);
        });

        expect(mockToastError).not.toHaveBeenCalled();
        expect(mockOnOpen).not.toHaveBeenCalled();
    });

    it("shows a toast and opens the modal when ?error=OAuthCallback is present", () => {
        mockSearchParamsGet = (key) =>
            key === "error" ? "OAuthCallback" : null;

        act(() => {
            render(<LoginModal />);
        });

        expect(mockToastError).toHaveBeenCalledWith(
            "Sign-in was cancelled or failed. Please try again.",
        );
        expect(mockOnOpen).toHaveBeenCalledTimes(1);
    });

    it("opens the modal for a native email magic-link request", () => {
        mockSearchParamsGet = (key) => {
            if (key === "nativeAuthProvider") return "email";
            if (key === "callbackUrl") {
                return "https://laugh-track.com/api/v1/auth/native/callback?provider=email";
            }
            return null;
        };

        act(() => {
            render(<LoginModal />);
        });

        expect(mockOnOpen).toHaveBeenCalledTimes(1);
        expect(mockToastError).not.toHaveBeenCalled();
    });

    it("ignores non-native callback URLs when deciding whether to open", () => {
        mockSearchParamsGet = (key) => {
            if (key === "nativeAuthProvider") return "email";
            if (key === "callbackUrl") return "https://attacker.example/auth";
            return null;
        };

        act(() => {
            render(<LoginModal />);
        });

        expect(mockOnOpen).not.toHaveBeenCalled();
    });

    it("removes the error param from the URL after handling", () => {
        Object.defineProperty(window, "location", {
            value: {
                href: "https://laugh-track.com/?error=OAuthCallback",
                origin: "https://laugh-track.com",
            },
            writable: true,
            configurable: true,
        });
        mockSearchParamsGet = (key) =>
            key === "error" ? "OAuthCallback" : null;

        act(() => {
            render(<LoginModal />);
        });

        expect(mockReplace).toHaveBeenCalledTimes(1);
        const [replacedUrl] = mockReplace.mock.calls[0] as [string, unknown];
        expect(replacedUrl).not.toContain("error=");
    });
});
