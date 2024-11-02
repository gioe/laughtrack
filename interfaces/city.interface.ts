import { ShowProvider } from "./";

export interface CityInterface extends ShowProvider {
    id: number;
    name: string;
}

export interface GetCitiesResponseDTO {
    city: string;
}
