/**
 * @vitest-environment happy-dom
 */
import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockSignIn, mockToastSuccess, mockToastError } = vi.hoisted(() => ({
    mockSignIn: vi.fn(),
    mockToastSuccess: vi.fn(),
    mockToastError: vi.fn(),
}));

let mockSearchParamsGet: (key: string) => string | null = () => null;

vi.mock("next-auth/react", () => ({
    signIn: mockSignIn,
}));

vi.mock("next/navigation", () => ({
    useSearchParams: () => ({ get: (key: string) => mockSearchParamsGet(key) }),
}));

vi.mock("react-hot-toast", () => ({
    default: {
        success: mockToastSuccess,
        error: mockToastError,
    },
}));

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({ mv: (value: number) => value }),
}));

vi.mock("../../auth/social", () => ({
    default: () => <div data-testid="social-auth-buttons" />,
}));

vi.mock("framer-motion", () => ({
    motion: {
        div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
            <div {...props}>{children}</div>
        ),
    },
}));

import LoginForm from "./index";

beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    mockSearchParamsGet = () => null;
    Object.defineProperty(window, "location", {
        value: {
            origin: "https://laughtrack.com",
        },
        writable: true,
        configurable: true,
    });
    mockSignIn.mockResolvedValue({ ok: true });
});

describe("LoginForm", () => {
    it("passes the native email callback URL through to Auth.js unchanged", async () => {
        const callbackUrl =
            "https://laughtrack.com/api/v1/auth/native/callback?provider=email";
        mockSearchParamsGet = (key) =>
            key === "callbackUrl" ? callbackUrl : null;

        render(<LoginForm onSubmit={vi.fn()} />);

        fireEvent.change(screen.getByPlaceholderText("you@example.com"), {
            target: { value: "fan@example.com" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Continue with Email" }),
        );

        await waitFor(() => {
            expect(mockSignIn).toHaveBeenCalledWith("email", {
                email: "fan@example.com",
                redirect: false,
                callbackUrl,
            });
        });
    });

    it("does not pass an unsafe callback URL into the magic-link request", async () => {
        mockSearchParamsGet = (key) =>
            key === "callbackUrl" ? "https://attacker.example/auth" : null;

        render(<LoginForm onSubmit={vi.fn()} />);

        fireEvent.change(screen.getByPlaceholderText("you@example.com"), {
            target: { value: "fan@example.com" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Continue with Email" }),
        );

        await waitFor(() => {
            expect(mockSignIn).toHaveBeenCalledWith("email", {
                email: "fan@example.com",
                redirect: false,
                callbackUrl: undefined,
            });
        });
    });
});
