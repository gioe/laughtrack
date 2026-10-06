/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { act } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { hydrateRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ShowDetailDTO } from "@/lib/data/show/detail/interface";

vi.mock("next/link", () => ({
    default: ({ children, ...props }: React.ComponentProps<"a">) => (
        <a {...props}>{children}</a>
    ),
}));
vi.mock("next/image", () => ({
    default: ({ alt, src }: React.ComponentProps<"img">) => (
        <img alt={alt} src={src} />
    ),
}));
vi.mock("framer-motion", () => ({
    motion: {
        article: ({ children }: React.PropsWithChildren) => (
            <article>{children}</article>
        ),
        div: ({ children }: React.PropsWithChildren) => <div>{children}</div>,
    },
}));
vi.mock("@/hooks", async () => {
    const { mockUseMotionProps } = await import("@/test/motionProps");
    return { useMotionProps: mockUseMotionProps, useDialogKeyboard: () => {} };
});
vi.mock("@/hooks/useFavorite", () => ({
    useFavorite: () => ({
        isFavorite: false,
        handleFavoriteClick: () => Promise.resolve(),
        isAuthenticated: false,
    }),
}));

const NativeDateTimeFormat = Intl.DateTimeFormat;
let root: Root | undefined;
let container: HTMLDivElement | undefined;

// Emulate two different ICU generations without depending on the test host's
// tzdata. Winter Denver/Los Angeles retain the old seasonal rules; fixed Etc
// zones emulate the updated server. No application formatter is mocked.
function installIntl(generation: "fresh" | "stale") {
    const zones: Record<string, string> =
        generation === "fresh"
            ? {
                  "America/Edmonton": "Etc/GMT+6",
                  "America/Vancouver": "Etc/GMT+7",
              }
            : {
                  "America/Edmonton": "America/Denver",
                  "America/Vancouver": "America/Los_Angeles",
              };
    const remap = (args: unknown[]) => {
        const [locale, options] = args as Parameters<
            typeof Intl.DateTimeFormat
        >;
        return [
            locale,
            options?.timeZone && zones[options.timeZone]
                ? { ...options, timeZone: zones[options.timeZone] }
                : options,
        ] as const;
    };
    Intl.DateTimeFormat = new Proxy(NativeDateTimeFormat, {
        construct: (_target, args) => new NativeDateTimeFormat(...remap(args)),
        apply: (_target, _receiver, args) =>
            NativeDateTimeFormat(...remap(args)),
    });
}

function nativeHour(date: Date, timeZone: string) {
    return new Intl.DateTimeFormat("en-US", {
        timeZone,
        hour: "2-digit",
        hourCycle: "h23",
    }).format(date);
}

async function surfaces(show: ShowDetailDTO) {
    // A browser has its own module graph. Reload date-fns-tz too, so a server
    // Intl formatter cached by timezone cannot mask client hydration drift.
    vi.resetModules();
    const [{ default: ShowCard }, { default: ShowTicketCta }] =
        await Promise.all([
            import("./index"),
            import("@/ui/pages/entity/show/ticketCta"),
        ]);
    return (
        <>
            <div data-surface="standard">
                <ShowCard show={show} />
            </div>
            <div data-surface="compact">
                <ShowCard show={show} density="compact" />
            </div>
            <div data-surface="detail">
                <ShowTicketCta show={show} isPast={false} />
            </div>
        </>
    );
}

afterEach(async () => {
    if (root) await act(async () => root?.unmount());
    root = undefined;
    container?.remove();
    container = undefined;
    Intl.DateTimeFormat = NativeDateTimeFormat;
    vi.unstubAllGlobals();
});

describe("venue time SSR hydration across ICU generations", () => {
    it.each([
        [
            "America/Edmonton",
            "2026-12-15T06:30:00Z",
            "December 15th at 12:30 am ABT",
            "00",
            "23",
        ],
        [
            "America/Vancouver",
            "2027-01-15T07:30:00Z",
            "January 15th at 12:30 am PT",
            "00",
            "23",
        ],
    ])(
        "preserves all card and detail text for %s",
        async (timezone, instant, expected, freshHour, staleHour) => {
            vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
            const show: ShowDetailDTO = {
                id: 4120,
                clubId: 24,
                name: "Winter Midnight Comedy",
                date: new Date(instant),
                timezone,
                clubName: "The Comedy Room",
                address: "123 Main St",
                imageUrl: "https://example.com/club.jpg",
                lineup: [],
                tickets: [],
                showPageUrl: "",
            };
            installIntl("fresh");
            expect(nativeHour(show.date, timezone)).toBe(freshHour);
            const server = await surfaces(show);
            container = document.createElement("div");
            container.innerHTML = renderToString(server);
            document.body.appendChild(container);
            const serverText = container.textContent;
            for (const surface of container.querySelectorAll(
                "[data-surface]",
            )) {
                expect(surface.textContent).toContain(expected);
            }

            installIntl("stale");
            // The stale native clock is an hour earlier AND on the previous date.
            // This guards against a vacuous test with equivalent server/client ICU.
            expect(nativeHour(show.date, timezone)).toBe(staleHour);
            const client = await surfaces(show);
            const recoverableErrors = vi.fn();
            await act(async () => {
                root = hydrateRoot(container!, client, {
                    onRecoverableError: recoverableErrors,
                });
            });
            expect(recoverableErrors).not.toHaveBeenCalled();
            expect(container.textContent).toBe(serverText);
            for (const surface of container.querySelectorAll(
                "[data-surface]",
            )) {
                expect(surface.textContent).toContain(expected);
            }
        },
    );
});
