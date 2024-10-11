import { GetShowResponseDTO } from "./show.interface.js";

export interface GetHomeSearchResultsDTO {
  location: string;
  start_date: string;
  end_date: string;
}

export interface GetHomeSearchResultsResponseDTO {
  city: string;
  dates: GetShowResponseDTO[];
  clubs: string[]
}

