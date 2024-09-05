import { runTasks } from "../../util/promiseUtil.js";
import { DateTimeScraper } from "./DateTimeScraper.js";
import { Comedian } from "../../classes/Comedian.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { TicketScraper } from "./TicketScraper.js";
import { ScrapingConfig } from "../../classes/ScrapingConfig.js";
import { Scrapable } from "../../api/interfaces/scrapable.interface.js";
import { ShowInterface } from "../../api/interfaces/show.interface.js";
import { Show } from "../../classes/Show.js";

export class ShowScraper {

  private comedianScraper: ComedianScraper;
  private dateTimeScraper: DateTimeScraper;
  private ticketScraper: TicketScraper;

  constructor(scrapingConfig: ScrapingConfig) {
    this.comedianScraper = new ComedianScraper(scrapingConfig);
    this.ticketScraper = new TicketScraper(scrapingConfig);
    this.dateTimeScraper = new DateTimeScraper(scrapingConfig);
  }

  scapeShow = async (scrapable: Scrapable, input?: any): Promise<ShowInterface> => {
    return this.comedianScraper.getAllComedianNames(scrapable)
    .then((comedians: Comedian[]) => this.runShowScrapingTasks(scrapable, comedians, input))
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