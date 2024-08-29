import { Club } from "../api/interfaces/club.interface.js";
import { Comedian } from "../api/interfaces/comedian.interface.js";
import { Show } from "../api/interfaces/show.interface.js";
import { formatShowTicketLink } from "../util/showUtil.js";
import { ComedianModel } from "./ComedianModel.js";
import { DateTimeContainer } from "./DateTimeContainer.js";

export class ShowModel implements Show {

  dateTime: Date = new Date();
  ticketLink: string = "";
  dateTimeString: string = "";
  path: string;
  comedians: Comedian[]
  clubId?: string

  constructor(scrapedValues: string[], comedians: ComedianModel[]) {
    this.comedians = comedians
    this.dateTimeString = scrapedValues[0]
    this.path = scrapedValues[1]
  }

  setClub = (club: Club) => {
    this.clubId = club.id;
    this.ticketLink = formatShowTicketLink(this.path, club);
    this.dateTime = new DateTimeContainer(this.dateTimeString, club.scrapingConfig).asDateObject();
  }

}