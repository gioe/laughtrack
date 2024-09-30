import { ClubDetailsInterface, ClubInterface } from "./club.interface.js";
import { ComedianInterface } from "./comedian.interface.js";

export interface ShowInterface {
    id: number;
    dateTime: Date;
    ticketLink: string
    club: ClubInterface;
  }

  export interface ShowDetailsInterface {
    id: number;
    city: string;
    club: ClubDetailsInterface;
    lineup: LineupItemInterface[];
    dateTime: string;
    ticketLink: string
  }

  export interface LineupItemInterface {
    id: number;
    name: string;
    popularityScore: number;
  }