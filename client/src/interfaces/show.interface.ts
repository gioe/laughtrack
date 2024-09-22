import { ClubInterface } from "./club.interface.js";
import { ComedianInterface } from "./comedian.interface.js";

export interface ShowInterface {
    dateTime: Date;
    ticketLink: string
    club: ClubInterface;
  }
