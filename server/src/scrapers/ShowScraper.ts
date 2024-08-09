import Scrapable from "../types/scrapable.interface.js";
import { runTasks } from "../util/types/promiseUtil.js";
import { DateTimeScraper } from "./DateTimeScraper.js";
import { Comedian } from "../classes/Comedian.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { TicketScraper } from "./TicketScraper.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";
import { Show } from "../classes/Show.js";
import { ShowDetailPageScraper } from "./ShowDetailPageScraper.js";

export class ShowScraper {

  private comedianScraper: ComedianScraper;
  private dateTimeScraper: DateTimeScraper;
  private ticketScraper: TicketScraper;
  private showDetailPageScraper = new ShowDetailPageScraper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.comedianScraper = new ComedianScraper(scrapingConfig);
    this.ticketScraper = new TicketScraper(scrapingConfig);
    this.dateTimeScraper = new DateTimeScraper(scrapingConfig);
  }
  
  scrapeShowDetailContainers = async (containers: Scrapable[]): Promise<Comedian[][]> => {
    console.log(containers.length)
    const tasks = containers.map(container => this.scrapeShowDetailContainer(container))
    return runTasks(tasks)
  }

  scrapeShowDetailPage = async (scrapable: Scrapable): Promise<Comedian[][]> => {
    return this.showDetailPageScraper.scrape(scrapable);
  }

  scrapeShowDetailContainer = async (scrapable: Scrapable): Promise<Comedian[]> => {
    return this.scrapeForComedians(scrapable)
  }

  scrapeForComedians = async (showDetailContainer: Scrapable): Promise<Comedian[]> => {
    return this.comedianScraper.getAllComedianNames(showDetailContainer)
      .then((comedians: Comedian[]) => this.runShowScrapingTasks(showDetailContainer, comedians))
  }

  runShowScrapingTasks = async (showComponent: Scrapable,
    comedians: Comedian[]): Promise<Comedian[]> => {
    const datetimeTask = this.dateTimeScraper.getShowDateTimeTask(showComponent)
    const ticketTask = this.ticketScraper.getShowTicketTask(showComponent)

    return runTasks([datetimeTask, ticketTask])
    .then((scrapedValues: any[]) => this.addShowToComedians(scrapedValues, comedians))
  }

  addShowToComedians = (scrapedValues: string[], comedians: Comedian[]) => {

    const show = new Show(scrapedValues)

    comedians.forEach((comedian: Comedian) => {
      comedian.addShow(show)
    })

    return comedians;
  }
  

}