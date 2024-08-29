import { Comedian } from "./comedian.interface.js";

export interface Show {
    dateTime: Date;
    ticketLink: string
    comedians?: Comedian[]
    comedianIds?: string[]
    id?: string
    clubId?: string
    createdAt?: Date
    updatedAt?: Date
    deletedAt?: Date 
  }