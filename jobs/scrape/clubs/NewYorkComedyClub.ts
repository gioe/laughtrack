import { Show } from "../../../classes/Show";
import { ClubScrapingData, ClubScraper, ScrapingOutput } from "../../../interfaces";
import { PageManager } from "../handlers/PageManager";
import playwright from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper";
import { generateValidUrl } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";

const LINK = "div.col-xs-12.col-sm-6.col-lg-7.upcoming-list-description.calendar-upcoming-list-description > a.btn.btn-default";
const MORE = "#--load-more-shows";
const DATE_TIME = "div.mobile-event-header.header.visible-xs";
const COMEDIAN_NAME = "p.comedian-name > a";
const SHOW_NAME = "span.date-div";
const PRICE = "div.event-ticket-type > span.ticket-price.original";
const TICKET_LINK = "span.date-div";
const SEPARATOR = " - ";

export class NewYorkComedyClub implements ClubScraper {

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
        console.log(`Error scraping New York Comedy Club: ${error}`)
        return []
      })
  }

  runClubScrapingFunction = async (page: playwright.Page): Promise<ScrapingOutput[]> => {
    const moreLocator = page.locator(MORE);
    return this.pageManager.expandPage(page, moreLocator)
      .then(page => {
        const linksLocator = page.locator(LINK);
        return this.pageManager.getAllLinksOnPage(page.url(), linksLocator)
      })
      .then((links: string[]) => this.runScrapingLoop(page, links))
  }

  runScrapingLoop = async (page: playwright.Page, links: string[]): Promise<ScrapingOutput[]> => {
    var scrapingOutput: ScrapingOutput[] = []

    for (let index = 0; index < links.length - 1; index++) {
      const input = links[index];
      const output = await this.navigateToUrlAndScrape(page, input)
      scrapingOutput.push(output)
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
          ticketLinkLocator: page.locator(TICKET_LINK),
          showNameLocator: page.locator(SHOW_NAME),
          priceLocator: page.locator(PRICE),
        })
      })
      .then((scrapingOutput: any[]) => this.processOutput(scrapingOutput, link))
  }


  processOutput = (output: any[], link: string): ScrapingOutput => {
    const show = new Show({
      lineup: output[0],
      dateTime: new DateTimeContainer(output[1], SEPARATOR).asDateObject(),
      ticketLink: generateValidUrl(this.clubData.baseUrl, link),
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