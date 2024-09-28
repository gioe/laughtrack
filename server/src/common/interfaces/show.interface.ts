import { ComedianInterface } from "./comedian.interface.js";

export interface ShowInterface {
    id: number
    dateTime: Date;
    ticketLink: string
    clubId: number
    popularityScore: number;
    comedians?: ComedianInterface[]
  }

  export interface ShowPopularityScore {
    id: number;
    popularity_score: number
  }