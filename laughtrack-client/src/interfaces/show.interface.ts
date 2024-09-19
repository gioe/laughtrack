import { ClubInterface } from "./club.interface.js";
import { ComedianInterface } from "./comedian.interface.js";

export interface ShowInterface {
    id: number
    dateTime: Date;
    ticketLink: string
    club: ClubInterface;
  }