export interface ComedianPodcastAppearanceDTO {
    id: number;
    podcastName: string;
    podcastImageUrl: string | null;
    podcastAuthorName: string | null;
    podcastWebsiteUrl: string | null;
    episodeTitle: string;
    releaseDate: Date | string | null;
    episodeUrl: string;
    audioUrl: string | null;
    durationSeconds: number | null;
    appearanceRole: string;
}
