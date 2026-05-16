export interface ComedianPodcastAppearanceDTO {
    id: number;
    podcastName: string;
    episodeTitle: string;
    releaseDate: Date | string | null;
    episodeUrl: string;
    audioUrl: string | null;
    durationSeconds: number | null;
    appearanceRole: string;
}
