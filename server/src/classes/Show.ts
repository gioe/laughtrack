import Comedian from "../database/models/Comedian.js";

export class Show {

  date?: string;
  time?: string;
  dateTime?: Date;
  ticketLink: string = ""
  comedians: Comedian[];

  constructor(scrapedValues: string[], 
    comedians: Comedian[]) {
      this.comedians = comedians;
  }

  setDate = (dateString: string) => {
    this.date = dateString
  }

  setTime = (timeString: string) => {
    this.time = timeString
  }

  setDateTime = (dateTime: Date) => {
    this.dateTime = dateTime
  }

  setTicketLink = (ticketLinkString: string) => {
    this.ticketLink = ticketLinkString
  }

}