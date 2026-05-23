import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { FilterDTO } from "@/objects/interface";

export interface PodcastEpisodeDTO {
    id: number;
    title: string;
    description: string | null;
    releaseDate: Date | string | null;
    durationSeconds: number | null;
    episodeUrl: string | null;
    audioUrl: string | null;
    appearances: PodcastEpisodeAppearanceDTO[];
}

export interface PodcastEpisodeAppearanceDTO {
    id: number;
    uuid: string;
    name: string;
    imageUrl: string;
}

export interface PodcastHostDTO {
    id: number;
    uuid: string;
    name: string;
    imageUrl: string;
}

export interface PodcastDTO {
    id: number;
    slug: string;
    title: string;
    authorName: string | null;
    websiteUrl: string | null;
    feedUrl: string | null;
    imageUrl: string | null;
    description: string | null;
    episodeCount: number;
    hosts: PodcastHostDTO[];
    isFavorite?: boolean;
}

export interface PodcastDetailResponse {
    podcast: PodcastDTO;
    episodes: PodcastEpisodeDTO[];
    relatedComedians: ComedianDTO[];
}

export interface PodcastSearchResponse {
    data: PodcastDTO[];
    total: number;
    filters: FilterDTO[];
}
