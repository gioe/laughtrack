import playwright from "playwright-core";
import { ComedianScraper } from "./ComedianScraper.js";
import { ScrapingConfig } from "./ScrapingConfig.js";
import { providedPromiseResponse, runTasks } from "../../../common/util/promiseUtil.js";
import { Show } from "../../../common/models/classes/Show.js";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { ShowInput } from "../../../common/models/interfaces/show.interface.js";
import { DateTimeContainer } from "../objectContainers/DateTimeContainer.js";
import { Comedian } from "../../../common/models/classes/Comedian.js";

export class ShowScraper {

  private comedianScraper: ComedianScraper;
  private scrapingConfig: ScrapingConfig;
  private scraper = new ScrapableScraper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig;
    this.comedianScraper = new ComedianScraper(scrapingConfig);
  }

  getShowLineup = async (page: playwright.Page): Promise<Comedian[]> => {
    return this.comedianScraper.scrapeComedians(page)
  }

  getShowDateTime = async (page: playwright.Page): Promise<Date> => {
    return this.scrapingConfig.dateTimeSelector ? this.getDateTime(page) : this.combineDateAndTime(page)
  }

  combineDateAndTime = async (page: playwright.Page): Promise<Date> => {
    return runTasks([this.getDate(page), this.getTime(page)])
    .then((scrapedValues: string[]) => new DateTimeContainer(scrapedValues).asDateObject());
  }

  getDateTime = async (page: playwright.Page): Promise<Date> => {
    if (this.scrapingConfig.dateTimeSelector) {
      console.log(page.url())
      return this.scraper.getTextContent(page, this.scrapingConfig.dateTimeSelector)
      .then((scrapedValues: string[]) => new DateTimeContainer(scrapedValues).asDateObject());
    }
    throw new Error(`No selector provided for datetime`)
  }

  getTicketLink = async (page: playwright.Page): Promise<string> => {
    const url = page.url()
    return providedPromiseResponse(url)
  }

  getName = async (page: playwright.Page): Promise<string> => {
    if (this.scrapingConfig.showNameSelector) {
      return this.scraper.getText(page.locator(this.scrapingConfig.showNameSelector))
    }
    throw new Error(`No selector provided scraping show name`)
  }

  scapeShow = async (page: playwright.Page): Promise<Show> => {
    const tasks = [this.getShowLineup(page), this.getShowDateTime(page), this.getTicketLink(page), this.getName(page)]

    return runTasks<any>(tasks)
      .then((scrapedValues: any[]) => {

        const input = {
          lineup: scrapedValues[0],
          dateTime: scrapedValues[1],
          ticketLink: scrapedValues[2],
          name: scrapedValues[3]
        } as ShowInput

        return new Show(input)

      })
  }

}