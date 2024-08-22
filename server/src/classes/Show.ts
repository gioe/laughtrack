export class Show {

  date?: string;
  time?: string;
  dateTime?: Date;
  ticketLink: string = ""

  constructor(scrapedValues: string[]) {

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