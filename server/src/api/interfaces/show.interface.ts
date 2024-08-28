import { Club } from "./club.interface.js";
import { Comedian } from "./comedian.interface.js";

export interface Show {
    dateTime: Date;
    ticketLink: string
    comedians?: Comedian[]
    comedianIds?: string[]
    id?: string
    clubId?: string
    club?: Club
    createdAt?: Date
    updatedAt?: Date
    deletedAt?: Date 
  }