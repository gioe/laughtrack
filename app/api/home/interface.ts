import { ClubDTO } from "@/objects/class/club/club.interface";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

export interface HomePageDataResponse {
    comedians: ComedianDTO[];
    clubs: ClubDTO[]
}
