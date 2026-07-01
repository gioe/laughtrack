import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { PaginatedEntityResponseDTO } from "@/objects/interface";
import { HomeCityFilterDTO } from "@/lib/data/filters/getComedianHomeCityFilters";
import { HomeClubFilterDTO } from "@/lib/data/filters/getComedianHomeClubFilters";

export type ComedianSearchResponse = PaginatedEntityResponseDTO<ComedianDTO> & {
    homeCityFilters: HomeCityFilterDTO[];
    homeClubFilters: HomeClubFilterDTO[];
};


export interface ComediansResponse {
    comedians: ComedianDTO[];
    totalCount: number;
}
