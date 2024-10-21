import { GetShowResponseDTO, ShowInterface } from "./show.interface.js";

// Client
export interface HomeSearchResultInterface {
  city: string;
  dates: ShowInterface[]
  clubs: string[]
}

// DB
export interface GetHomeSearchResultsDTO {
  location: string;
  start_date: string;
  end_date: string;
}

export interface GetHomeSearchResultsResponseDTO {
  city: string;
  dates: GetShowResponseDTO[];
  clubs: string[]
  price: string;
}

