import { Show } from "../../../common/models/classes/Show.js";
import { ClubScrapingData } from "../../../common/models/interfaces/club.interface.js";
import { ClubScraper, ScrapingOutput } from "../../../common/models/interfaces/scrape.interface.js";
import { PageManager } from "../handlers/PageManager.js";
import playwright from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper.js";
import { generateValidUrl } from "../../../common/util/primatives/urlUtil.js";
import { DateTimeContainer } from "../containers/DateTimeContainer.js";

const ALL_LINKS = "div.popover-event-container > div.event-single > div.event-info.clearfix > div.clearfix > a";
const NEXT = "div.calendar-next-btn > a";
const DATE_TIME = "p.event-page-date";
const COMEDIAN_NAME = "p.comedian-name > a";
const SHOW_NAME = "div.col-sm-12.text-center > h1";
const PRICE = "div.ticket-info-container > div.ticket-price";
const SEPARATOR = " - ";

export class WestSideComedyClub implements ClubScraper {

  private clubData: ClubScrapingData;
  private browser: playwright.Browser;
  private pageManager = new PageManager();
  private scraper = new ShowScraper();

  constructor(clubData: ClubScrapingData, browser: playwright.Browser) {
    this.clubData = clubData;
    this.browser = browser;
  }

  scrape = async (): Promise<ScrapingOutput[]> => {
    return this.browser.newPage()
      .then((page: playwright.Page) => this.pageManager.navigateToUrl(page, this.clubData.schedulePageUrl))
      .then((page: playwright.Page) => this.runClubScrapingFunction(page))
      .catch((error) => {
        console.log(`Error scraping West Side Comedy Club: ${error}`)
        return []
      })
  }

  runClubScrapingFunction = async (page: playwright.Page): Promise<ScrapingOutput[]> => {
    return this.pageManager.getLinksAcrossPages(page, NEXT, ALL_LINKS)
      .then((links: string[]) => this.runScrapingLoop(page, links))
  }

  runScrapingLoop = async (page: playwright.Page, links: string[]): Promise<ScrapingOutput[]> => {
    var scrapingOutput: ScrapingOutput[] = []

    for (let index = 0; index < links.length - 1; index++) {
      const input = links[index];
      const show = await this.navigateToUrlAndScrape(page, input)
      scrapingOutput.push(show)
    }

    await this.browser.close();
    return scrapingOutput
  }

  navigateToUrlAndScrape = async (page: playwright.Page, link: string): Promise<ScrapingOutput> => {
    return this.pageManager.navigateToUrl(page, link)
      .then((page) => {
        return this.scraper.scrape({
          comedianNameLocator: page.locator(COMEDIAN_NAME),
          dateTimeLocator: page.locator(DATE_TIME),
          showNameLocator: page.locator(SHOW_NAME),
          priceLocator: page.locator(PRICE),
        })
      })
      .then((scrapingOutput: any[]) => this.processOutput(scrapingOutput, link))
  }

  processOutput = (output: any[], url: string): ScrapingOutput => {
    const show = new Show({
      lineup: output[0],
      dateTime: new DateTimeContainer(output[1], SEPARATOR).asDateObject(),
      ticketLink: generateValidUrl(this.clubData.baseUrl, url),
      name: output[3],
      price: output[4],
      clubId: this.clubData.id,
    })
    return {
      show: show.asCreateShowDTO(),
      comedians: show.asCreateComedianDTOArray()
    } as ScrapingOutput
  }


}