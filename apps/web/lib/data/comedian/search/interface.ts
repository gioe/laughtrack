import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { PaginatedEntityResponseDTO } from "@/objects/interface";
import { HomeCityFilterDTO } from "@/lib/data/filters/getComedianHomeCityFilters";

export type ComedianSearchResponse = PaginatedEntityResponseDTO<ComedianDTO> & {
    homeCityFilters: HomeCityFilterDTO[];
};

export interface ComediansResponse {
    comedians: ComedianDTO[];
    totalCount: number;
}
