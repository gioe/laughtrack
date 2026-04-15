import { ClubDTO } from "@/objects/class/club/club.interface";
import { PaginatedEntityResponseDTO } from "@/objects/interface";
import { ChainFilterDTO } from "@/lib/data/filters/getChainFilters";

export type ClubSearchResponse = PaginatedEntityResponseDTO<ClubDTO> & {
    chainFilters: ChainFilterDTO[];
};

export interface ClubsResponse {
    clubs: ClubDTO[];
    totalCount: number;
}
