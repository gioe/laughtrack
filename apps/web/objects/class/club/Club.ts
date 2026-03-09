import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Show } from "../show/Show";
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
    readonly imageUrl: string;
    readonly phoneNumber: string;
    readonly fallbackImageUrl?: URL;

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
        this.phoneNumber = input.phone_number ?? "";

        this.imageUrl = input.imageUrl;

        // Initialize arrays and complex objects
        this.tagIds = input.tags ?? [];
        this.containedEntities =
            input.dates?.map((date) => new Show(date)) ?? [];
        this.socialData = input.social_data
            ? new SocialData(input.social_data)
            : undefined;

        // Initialize flags and counts
        this.isFavorite = input.is_Favorite ?? false;
        this.showCount = input.show_count;
        this.activeComedianCount = input.active_comedian_count;
    }
}
