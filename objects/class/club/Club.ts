import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Show } from "../show/Show";
import { ShowDTO } from "../show/show.interface";
import { SocialData } from "../socialData/SocialData";
import { ClubDTO, ClubInterface } from "./club.interface";

export class Club implements ClubInterface {
    // Required properties
    readonly id: number;
    readonly type: EntityType = EntityType.Club;
    readonly name: string;
    readonly containedEntities: Entity[];

    // Optional properties with default values
    readonly website: string;
    readonly city: string;
    readonly address: string;
    readonly zipCode: string;
    readonly isFavorite: boolean;
    readonly tagIds: number[];
    readonly showCount?: number;
    readonly activeComedianCount?: number;

    // Media-related properties
    readonly bannerImageUrl: URL | null;
    readonly cardImageUrl: URL | null;
    readonly fallbackImageUrl: URL;

    // Complex objects
    readonly socialData?: SocialData;

    constructor(input: ClubDTO) {
        // Initialize required properties
        this.id = input.id ?? 0;
        this.name = input.name ?? "";

        // Initialize location-related properties
        this.website = input.website ?? "";
        this.city = input.city ?? "";
        this.address = input.address ?? "";
        this.zipCode = input.zipCode ?? "";

        // Initialize media URLs
        const cdnHost = "laughtrack.b-cdn.net";
        if (!cdnHost) {
            throw new Error('NEXT_PUBLIC_BUNNYCDN_CDN_HOST environment variable is not set');
        }

        this.fallbackImageUrl = new URL(`logo.png`, `https://${cdnHost}/`);
        this.cardImageUrl = new URL(`/clubs/${input.name}.png`, `https://${cdnHost}/`);
        this.bannerImageUrl = null; // Add logic if needed

        // Initialize arrays and complex objects
        this.tagIds = input.tags ?? [];
        this.containedEntities = this.initializeContainedEntities(input.dates);
        this.socialData = input.social_data ? new SocialData(input.social_data) : undefined;

        // Initialize flags and counts
        this.isFavorite = input.is_Favorite ?? false;
        this.showCount = input.show_count;
        this.activeComedianCount = input.active_comedian_count
    }

    private initializeContainedEntities(dates?: ShowDTO[]): Show[] {
        return dates?.map(date => new Show(date)) ?? [];
    }

    getShows(): Show[] {
        return this.containedEntities as Show[];
    }
}
