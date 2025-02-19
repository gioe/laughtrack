import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { PaginatedEntityResponseDTO } from "@/objects/interface";

export type ComedianSearchResponse = PaginatedEntityResponseDTO<ComedianDTO>;


export interface ComediansResponse {
    comedians: ComedianDTO[];
    totalCount: number;
}
