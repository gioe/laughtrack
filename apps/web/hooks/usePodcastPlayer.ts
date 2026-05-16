import { create } from "zustand";

export interface PodcastPlayerEpisode {
    id: number;
    podcastName: string;
    episodeTitle: string;
    episodeUrl: string;
    audioUrl: string;
}

interface PodcastPlayerState {
    currentEpisode: PodcastPlayerEpisode | null;
    isPlaying: boolean;
    loadError: boolean;
    startEpisode: (episode: PodcastPlayerEpisode) => void;
    play: () => void;
    pause: () => void;
    fail: () => void;
    reset: () => void;
}

const initialState = {
    currentEpisode: null,
    isPlaying: false,
    loadError: false,
};

export const usePodcastPlayer = create<PodcastPlayerState>((set) => ({
    ...initialState,
    startEpisode: (episode) =>
        set({
            currentEpisode: episode,
            isPlaying: true,
            loadError: false,
        }),
    play: () => set({ isPlaying: true, loadError: false }),
    pause: () => set({ isPlaying: false }),
    fail: () => set({ isPlaying: false, loadError: true }),
    reset: () => set(initialState),
}));

export function startPodcastEpisode(episode: PodcastPlayerEpisode) {
    usePodcastPlayer.getState().startEpisode(episode);
}
