import playwright from "playwright-core";
import { ComedianScraper } from "./ComedianScraper.js";
import { ScrapingConfig } from "./ScrapingConfig.js";
import { providedPromiseResponse, runTasks } from "../../../common/util/promiseUtil.js";
import { Show } from "../../../common/models/classes/Show.js";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { ShowInput } from "../../../common/models/interfaces/show.interface.js";
import { DateTimeContainer } from "../objectContainers/DateTimeContainer.js";
import { Comedian } from "../../../common/models/classes/Comedian.js";
import { isEventbritePage } from "../../../common/util/primatives/urlUtil.js";

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
    const selector = isEventbritePage(page) ? this.scrapingConfig.eventbriteDateTimeSelector : this.scrapingConfig.dateTimeSelector
    
    if (selector) {
      return this.scraper.getTextContent(page, selector, this.scrapingConfig.dateTimeContainer)
        .then((scrapedValues: string[]) => new DateTimeContainer(scrapedValues, this.scrapingConfig.dateTimeSeparator).asDateObject())
        .catch((error) => {
          console.error(`Error getting show datetime: ${error}`)
          return new DateTimeContainer([], this.scrapingConfig.dateTimeSeparator).asDateObject()
        })
    }

    throw new Error(`No selector provided for datetime`)
  }

  getTicketLink = async (page: playwright.Page): Promise<string> => {
    const url = page.url()
    return providedPromiseResponse(url)
  }

  getName = async (page: playwright.Page): Promise<string> => {
    const selector = isEventbritePage(page) ? this.scrapingConfig.eventbriteShowNameSelector : this.scrapingConfig.showNameSelector
   
    if (selector) {
      return this.scraper.getText(page.locator(selector))
        .catch((error) => {
          console.error(`Error getting show name: ${error}`)
          return ""
        })
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