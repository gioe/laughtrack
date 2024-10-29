import { Show } from "../../../classes/Show";
import { ClubScrapingData, ClubScraper, ScrapingOutput } from "../../../interfaces";
import { PageManager } from "../handlers/PageManager";
import playwright from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper";
import { generateValidUrl, isEventbritePage } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";

const LINK = "div.event-cta-button > a";
const DATE_TIME = "div.date > div.datetime-location-content";
const EVENTBRITE_DATE_TIME = "span.date-info__full-datetime > div"
const SHOW_NAME = "#event-name > a";
const EVENTBRITE_SHOW_NAME = "h1.event-title.css-0"
const PRICE = "div.content.pure-u-md-1-5.pure-u-1-2.price";
const EVENTBRITE_PRICE = "div.event-ticket-type > span.ticket-price.original";

export class Rodneys implements ClubScraper {

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
        console.log(`Error scraping Rodney's: ${error}`)
        return []
      })
  }

  runClubScrapingFunction = async (page: playwright.Page): Promise<ScrapingOutput[]> => {
    const linksLocator = page.locator(LINK);
    return this.pageManager.getAllLinksOnPage(page.url(), linksLocator)
      .then((links: string[]) => this.runScrapingLoop(page, links))
  }

  runScrapingLoop = async (page: playwright.Page, links: string[]): Promise<ScrapingOutput[]> => {
    var scrapedOutput: ScrapingOutput[] = []

    for (let index = 0; index < links.length - 1; index++) {
      const input = links[index];
      const output = await this.navigateToUrlAndScrape(page, input)
      scrapedOutput.push(output)
    }

    await this.browser.close()
    return scrapedOutput
  }

  navigateToUrlAndScrape = async (page: playwright.Page, link: string): Promise<ScrapingOutput> => {
    return this.pageManager.navigateToUrl(page, link)
      .then((page) => {
        const dateTimeSelector = isEventbritePage(page) ? EVENTBRITE_DATE_TIME : DATE_TIME
        const showNameSelector = isEventbritePage(page) ? EVENTBRITE_SHOW_NAME : SHOW_NAME
        const priceSelector = isEventbritePage(page) ? EVENTBRITE_PRICE : PRICE

        return this.scraper.scrape({
          dateTimeLocator: page.locator(dateTimeSelector),
          showNameLocator: page.locator(showNameSelector),
          priceLocator: page.locator(priceSelector),
        })
      })
      .then((scrapingOutput: any[]) => this.processOutput(scrapingOutput, link))
  }


  processOutput = (output: any[], url: string): ScrapingOutput => {
    const show = new Show({
      lineup: output[0],
      dateTime: new DateTimeContainer(output[1]).asDateObject(),
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