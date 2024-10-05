
import { Comedian } from "./Comedian.js";
import { DateTimeContainer } from "../../jobs/scrapers/containers/DateTimeContainer.js";
import { CreateShowDTO } from "../interfaces/data/show.interface.js";
import { ScrapingConfig } from "./ScrapingConfig.js";
import { CreateComedianDTO } from "../interfaces/data/comedian.interface.js";

export class Show {

  lineup: Comedian[];
  scrapingConfig: ScrapingConfig;
  dateTimeContainer: DateTimeContainer;
  ticketLink: string;

  clubId: number = 0;

  constructor(scrapedValues: string[], lineup: Comedian[], scrapingConfig: ScrapingConfig) {
    const dateTimeString = scrapedValues[0]
    const ticketString = scrapedValues[1]
    this.scrapingConfig = scrapingConfig;
    this.lineup = lineup
    this.ticketLink = ticketString;
    this.dateTimeContainer = new DateTimeContainer(dateTimeString, this.scrapingConfig);
  }

  setClubId = (id: number) => {
    this.clubId = id;
  }

  asCreateShowDTO = (): CreateShowDTO | null => {
    if (!this.isValid()) return null
    return {
      club_id: this.clubId,
      date_time: this.dateTimeContainer.asDateObject(),
      ticket_link: this.ticketLink,
    }
  }

  asCreateComedianDTOArray = (): CreateComedianDTO[] => {
    return this.lineup.map((comedian: Comedian) => comedian.asCreateComedianDTO())
  }

  isValid = (): boolean => {
    return this.clubId !== 0 && this.dateTimeContainer.isValid()
  }
 
}