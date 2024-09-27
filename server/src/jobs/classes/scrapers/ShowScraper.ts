import { runTasks } from "../../../common/util/promiseUtil.js";
import { DateTimeScraper } from "./DateTimeScraper.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { TicketScraper } from "./TicketScraper.js";
import { Scrapable } from "../../../common/interfaces/scrapable.interface.js";
import { ShowInterface } from "../../../common/interfaces/show.interface.js";
import { Comedian } from "../models/Comedian.js";
import { ScrapingConfig } from "../models/ScrapingConfig.js";
import { Show } from "../models/Show.js";
import { ClubInterface } from "../../../common/interfaces/club.interface.js";

export class ShowScraper {

  private comedianScraper: ComedianScraper;
  private dateTimeScraper: DateTimeScraper;
  private ticketScraper: TicketScraper;

  constructor(club: ClubInterface, scrapingConfig: ScrapingConfig) {
    this.comedianScraper = new ComedianScraper(club, scrapingConfig);
    this.ticketScraper = new TicketScraper(scrapingConfig);
    this.dateTimeScraper = new DateTimeScraper(scrapingConfig);
  }

  scapeShow = async (scrapable: Scrapable, input?: any): Promise<ShowInterface> => {
    return this.comedianScraper.getAllComedianData(scrapable)
    .then((comedians: Comedian[]) => {
      console.log(comedians)
      return this.runShowScrapingTasks(scrapable, comedians, input)
    })
  } 

  runShowScrapingTasks = async (scrapable: Scrapable,
    comedians: Comedian[],
    input?: any): Promise<ShowInterface> => {
        
    const ticketTask = this.ticketScraper.getShowTicketTask(scrapable, input)
    const datetimeTask = this.dateTimeScraper.getShowDateTimeTask(scrapable, input)

    return runTasks([datetimeTask, ticketTask])
    .then((scrapedValues: any[]) => this.addComediansToShow(scrapedValues, comedians))
  }

  addComediansToShow = (scrapedValues: string[], comedians: Comedian[]): ShowInterface => {
    return new Show(scrapedValues, comedians)
  }
  
}