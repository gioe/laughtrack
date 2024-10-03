
import { Comedian } from "./Comedian.js";
import { formatShowTicketLink } from "../util/showUtil.js";
import { DateTimeContainer } from "../../jobs/scrapers/containers/DateTimeContainer.js";
import { ClubInterface } from "../interfaces/client/club.interface.js";

export class Show {

  lineup: Comedian[];
  dateTimeString: string;
  path: string;

  clubId: number = 0;
  dateTime: Date = new Date();
  ticketLink: string = "";
  isValid: boolean = true;

  constructor(scrapedValues: string[], lineup: Comedian[]) {
    this.lineup = lineup
    this.dateTimeString = scrapedValues[0]
    this.path = scrapedValues[1]
  }

  setClub = (club: ClubInterface) => {
    this.clubId = club.id;
    this.ticketLink = formatShowTicketLink(this.path, club);
    this.handleDateTime(club)
  }

  handleDateTime = (club: ClubInterface) => {
    if (this.dateTimeString !== undefined) {
      const dateTimeContainer = new DateTimeContainer(this.dateTimeString, club.scrapingConfig);
      this.isValid = dateTimeContainer.isValid();
      this.dateTime = dateTimeContainer.asDateObject();
    }
  }

}