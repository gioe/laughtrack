import { GetShowResponseDTO } from "./show.interface.js";

export interface GetHomeSearchResultsDTO {
  location: string;
  start_date: string;
  end_date: string;
  comedians?: string;
  clubs?: string; 
  sort?: string;
}

export interface GetHomeSearchResultsResponseDTO {
  city: string;
  dates: GetShowResponseDTO[];
  clubs: string[]
}

