/** @vitest-environment happy-dom */
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import PodcastDiscoveryRail from "./PodcastDiscoveryRail";
import { usePodcastPlayer } from "@/hooks/usePodcastPlayer";

let enter: () => void;
let fetcher: ReturnType<typeof vi.fn>;
beforeEach(() => {
    usePodcastPlayer.getState().reset();
    fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal(
        "IntersectionObserver",
        class {
            constructor(callback: (entries: unknown[]) => void) {
                enter = () => callback([{ isIntersecting: true }]);
            }
            observe() {}
            unobserve() {}
            disconnect() {}
        },
    );
});
afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});
const episode = {
    id: 1,
    title: "A great conversation",
    audioUrl: "https://example.com/episode.mp3",
    podcast: {
        id: 4,
        slug: "comedy-hour",
        title: "Comedy Hour",
        imageUrl: null,
    },
    recommendation: {
        appearanceRole: "guest",
        comedian: { name: "Avery Stone" },
    },
};
it("waits for the rail to approach, renders attribution, and plays only on click", async () => {
    fetcher.mockResolvedValue({
        ok: true,
        json: async () => ({ data: { episodes: [episode] } }),
    });
    render(<PodcastDiscoveryRail />);
    expect(fetcher).not.toHaveBeenCalled();
    await act(async () => enter());
    expect(
        screen.getByRole("link", { name: "Avery Stone" }).getAttribute("href"),
    ).toBe("/comedian/Avery%20Stone");
    expect(
        screen.getByRole("link", { name: episode.title }).getAttribute("href"),
    ).toBe("/podcast/comedy-hour");
    expect(usePodcastPlayer.getState().currentEpisode).toBeNull();
    fireEvent.click(
        screen.getByRole("button", { name: `Play ${episode.title}` }),
    );
    expect(usePodcastPlayer.getState().currentEpisode?.audioUrl).toBe(
        episode.audioUrl,
    );
});
it.each(["empty", "error"])(
    "omits the optional rail on %s without affecting the page",
    async (kind) => {
        fetcher.mockResolvedValue({
            ok: kind !== "error",
            json: async () => ({ data: { episodes: [] } }),
        });
        render(
            <>
                <h1>Discover</h1>
                <PodcastDiscoveryRail />
            </>,
        );
        await act(async () => enter());
        expect(screen.getByRole("heading", { name: "Discover" })).toBeTruthy();
        expect(screen.queryByTestId("podcast-discovery-rail")).toBeNull();
    },
);
it("aborts an in-flight request when unmounted", async () => {
    fetcher.mockReturnValue(new Promise(() => {}));
    const view = render(<PodcastDiscoveryRail />);
    await act(async () => enter());
    const signal = fetcher.mock.calls[0][1].signal;
    view.unmount();
    expect(signal.aborted).toBe(true);
});
