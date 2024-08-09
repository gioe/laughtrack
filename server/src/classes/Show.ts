import { ShowInterface } from "../types/show.interface.js";

export class Show implements ShowInterface {

  date?: string;
  time?: string;
  dateTime?: Date;
  ticketLink: string = ""

  constructor(scrapedValues: string[]) {
  // const dateTime = scrapedShow.dateTimeContainer.asDateObject()
  // const ticketLink = formatShowTicketLink(scrapedShow.ticketString, club);
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