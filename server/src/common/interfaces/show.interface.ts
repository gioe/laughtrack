import { ClubDetailsInterface, ClubInterface } from "./club.interface.js";

export interface ShowInterface {
    id: number;
    dateTime: Date;
    ticketLink: string
    club: ClubInterface;
    popularityScore: number;
  }

  export interface ShowPopularityScore {
    id: number;
    popularityScore: number
  }

  export interface ShowDetailsInterface {
    id: number;
    city: string;
    club: any;
    dateTime: string;
    ticketLink: string;
    lineup: LineupItemInterface[]
  }

  export interface LineupItemInterface {
    id: number;
    name: string;
    popularityScore: number;
  }
