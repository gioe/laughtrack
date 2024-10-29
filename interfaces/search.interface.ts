import { GetShowResponseDTO, ShowInterface } from "./";

// Client
export interface HomeSearchResultInterface {
  city: string;
  shows: ShowInterface[]
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
