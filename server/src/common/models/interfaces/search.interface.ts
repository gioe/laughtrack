import { GetShowResponseDTO, ShowInterface } from "./show.interface.js";

// Client
export interface HomeSearchResultInterface {
    city: string;
    dates: ShowInterface[]
    clubs: string[]
}

// Data
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
  
  