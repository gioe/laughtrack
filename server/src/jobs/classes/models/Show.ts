import { ClubInterface } from "../../../common/interfaces/club.interface.js";
import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js";
import { ShowInterface } from "../../../common/interfaces/show.interface.js";
import { formatShowTicketLink } from "../../util/showUtil.js";
import { Comedian } from "./Comedian.js";
import { DateTimeContainer } from "../containers/DateTimeContainer.js";
import { Club } from "./Club.js";

export class Show implements ShowInterface {

  id: number = 0;
  dateTime: Date = new Date();
  ticketLink: string = "";
  dateTimeString: string = "";
  path: string;
  comedians: ComedianInterface[]
  club: ClubInterface;
  isValid: boolean = true;
  popularityScore: number = 0;

  constructor(scrapedValues: string[], comedians: Comedian[]) {
    this.club = new Club;
    this.comedians = comedians
    this.dateTimeString = scrapedValues[0]
    this.path = scrapedValues[1]
  }

  setClub = (club: ClubInterface) => {
    this.club = club;
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