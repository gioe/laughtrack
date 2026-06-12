import { SocialDataDTO } from "../socialData/socialData.interface";

// Lineup items hydrate only the popularity slice of social data — it feeds
// headliner hero selection (util/show/showHeroImage.ts) on web and iOS. The
// full social profile (followers, handles, linktree) stays on the comedian
// detail payload, so those fields are optional here; a full SocialDataDTO
// remains assignable. The v1 SocialData schema requires only `id`, so
// emitting the subset is contract-compatible with the generated iOS client.
export type LineupSocialDataDTO = Pick<SocialDataDTO, "id" | "popularity"> &
    Partial<Omit<SocialDataDTO, "id" | "popularity">>;

/**
 * Lightweight comedian shape used for show lineup items.
 * Extracted here to break the circular import between comedian.interface.ts
 * and show.interface.ts (ComedianDTO.dates references ShowDTO, which
 * references ComedianLineupDTO).
 */
export interface ComedianLineupDTO {
    name: string;
    imageUrl: string;
    hasImage?: boolean;
    uuid: string;
    id: number;
    userId?: number;
    socialData?: LineupSocialDataDTO;
    isFavorite?: boolean;
    showCount?: number;
    role?: string | null;
    isAlias?: boolean;
    parentComedian?: ComedianLineupDTO;
    lineupItems?: ComedianLineupItemDTO[];
}

export interface ComedianLineupItemDTO {
    comedian: ComedianLineupDTO;
    role?: string | null;
}
