import { Show } from "../../../classes/Show";
import { ClubScrapingData, ClubScraper, ScrapingOutput } from "../../../interfaces";
import { PageManager } from "../handlers/PageManager";
import playwright from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper";
import { generateValidUrl } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";
import { delay } from "../../../util/promiseUtil";

const LINK = "a.button.eventColl-statusBtn.eventColl-statusBtn--buy";
const DATE_TIME = "span.date-info__full-datetime > div";
const COMEDIAN_NAME = "ul.performers__list > li.supporters";
const SHOW_NAME = "h1.event-title.css-0";
const PRICE = "#event-description > div:nth-child(2) > div > p:nth-child(2) > strong > strong";

export class UnionHall implements ClubScraper {

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
        console.log(`Error scraping Union Hall: ${error}`)
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

    await this.browser.close();
    return scrapedOutput
  }

  navigateToUrlAndScrape = async (page: playwright.Page, link: string): Promise<ScrapingOutput> => {
    return this.pageManager.navigateToUrl(page, link)
      .then(() => delay(3000))
      .then(() => {
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
      dateTime: new DateTimeContainer(output[1]).asDateObject(),
      ticketLink: generateValidUrl(this.clubData.schedulePageUrl, url),
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