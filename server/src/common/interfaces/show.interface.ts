import { ComedianInterface } from "./comedian.interface.js";

export interface ShowInterface {
    id?: number
    dateTime: Date;
    ticketLink: string
    comedians: ComedianInterface[]
    clubId: number
  }