import { CityDTO } from "../../objects/class/city/city.interface";
import { ComedianDTO } from "../../objects/class/comedian/comedian.interface";
import { ClubActivityDTO } from "../../objects/class/club/club.interface";

export interface HomePageDTO {
    cities: CityDTO[];
    comedians: ComedianDTO[];
    clubs: ClubActivityDTO[]
}

export interface HomePageDataResponse { response: HomePageDTO }
