import { SocialDataDTO } from "../socialData/socialData.interface";

/**
 * Lightweight comedian shape used for show lineup items.
 * Extracted here to break the circular import between comedian.interface.ts
 * and show.interface.ts (ComedianDTO.dates references ShowDTO, which
 * references ComedianLineupDTO).
 */
export interface ComedianLineupDTO {
    name: string;
    imageUrl: string;
    uuid: string;
    id: number;
    userId?: number;
    social_data?: SocialDataDTO;
    isFavorite?: boolean;
    show_count?: number;
    isAlias?: boolean;
    parentComedian?: ComedianLineupDTO;
    lineupItems?: any[];
}
