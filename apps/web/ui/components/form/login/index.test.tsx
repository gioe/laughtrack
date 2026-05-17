/**
 * @vitest-environment happy-dom
 */
import type { ComponentProps } from "react";
import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
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
    useMotionProps: () => ({
        mv: <T,>(value: T) => value,
        mp: <T,>(value: T) => value,
        mt: <T,>(value: T) => value,
    }),
}));

vi.mock("../../auth/social", () => ({
    default: ({
        handleAppleSignin,
        handleGoogleSignin,
    }: {
        handleAppleSignin: () => void;
        handleGoogleSignin: () => void;
    }) => (
        <div data-testid="social-auth-buttons">
            <button type="button" onClick={handleGoogleSignin}>
                Continue with Google
            </button>
            <button type="button" onClick={handleAppleSignin}>
                Continue with Apple
            </button>
        </div>
    ),
}));

vi.mock("framer-motion", () => ({
    motion: {
        div: ({
            children,
            ...props
        }: ComponentProps<"div"> & {
            variants?: unknown;
            initial?: unknown;
            animate?: unknown;
            transition?: unknown;
        }) => {
            const domProps = { ...props };
            delete domProps.variants;
            delete domProps.initial;
            delete domProps.animate;
            delete domProps.transition;
            return <div {...domProps}>{children}</div>;
        },
        button: ({
            children,
            ...props
        }: ComponentProps<"button"> & {
            whileHover?: unknown;
            whileTap?: unknown;
        }) => {
            const domProps = { ...props };
            delete domProps.whileHover;
            delete domProps.whileTap;
            return <button {...domProps}>{children}</button>;
        },
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

describe("LoginForm native auth callbacks", () => {
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

    it("passes a native Google callback URL into NextAuth social sign-in", async () => {
        const callbackUrl =
            "https://laughtrack.com/api/v1/auth/native/callback?provider=google";
        mockSearchParamsGet = (key) =>
            key === "callbackUrl" ? callbackUrl : null;

        render(<LoginForm onSubmit={vi.fn()} />);

        fireEvent.click(screen.getByRole("button", { name: /google/i }));

        await waitFor(() => {
            expect(mockSignIn).toHaveBeenCalledWith("google", {
                callbackUrl,
            });
        });
    });

    it("passes a native Apple callback URL into NextAuth social sign-in", async () => {
        const callbackUrl =
            "https://laughtrack.com/api/v1/auth/native/callback?provider=apple";
        mockSearchParamsGet = (key) =>
            key === "callbackUrl" ? callbackUrl : null;

        render(<LoginForm onSubmit={vi.fn()} />);

        fireEvent.click(screen.getByRole("button", { name: /apple/i }));

        await waitFor(() => {
            expect(mockSignIn).toHaveBeenCalledWith("apple", {
                callbackUrl,
            });
        });
    });
});
