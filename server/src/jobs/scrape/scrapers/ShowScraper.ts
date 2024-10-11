import { DateTimeScraper } from "./DateTimeScraper.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { TicketScraper } from "./TicketScraper.js";
import { ScrapingConfig } from "../../../common/models/classes/ScrapingConfig.js";
import { runTasks } from "../../../common/util/promiseUtil.js";
import { Scrapable } from "../../../common/models/interfaces/scrape.interface.js";
import { Comedian } from "../../../common/models/classes/Comedian.js";
import { Show } from "../../../common/models/classes/Show.js";

export class ShowScraper {

  private comedianScraper: ComedianScraper;
  private dateTimeScraper: DateTimeScraper;
  private ticketScraper: TicketScraper;
  private scrapingConfig: ScrapingConfig;

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig;
    this.comedianScraper = new ComedianScraper(scrapingConfig);
    this.ticketScraper = new TicketScraper(scrapingConfig);
    this.dateTimeScraper = new DateTimeScraper(scrapingConfig);
  }

  scapeShow = async (scrapable: Scrapable, input?: any): Promise<Show> => {
    return this.comedianScraper.getAllComedianData(scrapable)
    .then((comedians: Comedian[]) => this.runShowScrapingTasks(scrapable, comedians, input))
  } 

  runShowScrapingTasks = async (scrapable: Scrapable,
    comedians: Comedian[],
    input?: any): Promise<Show> => {
        
    const ticketTask = this.ticketScraper.getShowTicketTask(scrapable, input)
    const datetimeTask = this.dateTimeScraper.getShowDateTimeTask(scrapable, input)

    return runTasks([datetimeTask, ticketTask])
    .then((scrapedValues: any[]) => this.addComediansToShow(scrapedValues, comedians))
  }

  addComediansToShow = (scrapedValues: string[], comedians: Comedian[]): Show => {
    return new Show(scrapedValues, comedians, this.scrapingConfig)
  }
  
}