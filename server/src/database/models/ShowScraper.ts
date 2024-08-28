import { runTasks } from "../../util/promiseUtil.js";
import { DateTimeScraper } from "./DateTimeScraper.js";
import { ComedianModel } from "../../classes/ComedianModel.js";
import { Comedian } from "../../api/interfaces/comedian.interface.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { TicketScraper } from "./TicketScraper.js";
import { ScrapingConfig } from "../../classes/ScrapingConfig.js";
import { Scrapable } from "../../api/interfaces/scrapable.interface.js";
import { Show } from "../../api/interfaces/show.interface.js";
import { ShowModel } from "../../classes/ShowModel.js";

export class ShowScraper {

  private comedianScraper: ComedianScraper;
  private dateTimeScraper: DateTimeScraper;
  private ticketScraper: TicketScraper;

  constructor(scrapingConfig: ScrapingConfig) {
    this.comedianScraper = new ComedianScraper(scrapingConfig);
    this.ticketScraper = new TicketScraper(scrapingConfig);
    this.dateTimeScraper = new DateTimeScraper(scrapingConfig);
  }

  scapeShow = async (scrapable: Scrapable, input?: any): Promise<Show> => {
    console.log("Scraping show")
    
    return this.comedianScraper.getAllComedianNames(scrapable)
    .then((comedians: ComedianModel[]) => this.runShowScrapingTasks(scrapable, comedians, input))
  } 

  runShowScrapingTasks = async (scrapable: Scrapable,
    comedians: ComedianModel[],
    input?: any): Promise<Show> => {
      
    const ticketTask = this.ticketScraper.getShowTicketTask(scrapable, input)
    const datetimeTask = this.dateTimeScraper.getShowDateTimeTask(scrapable, input)

    return runTasks([datetimeTask, ticketTask])
    .then((scrapedValues: any[]) => this.addComediansToShow(scrapedValues, comedians))
  }

  addComediansToShow = (scrapedValues: string[], comedians: ComedianModel[]): Show => {
    return new ShowModel(scrapedValues, comedians)
  }
  
}