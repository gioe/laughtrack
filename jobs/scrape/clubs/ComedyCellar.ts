import { Show } from "../../../classes/Show";
import { ClubScrapingData, ClubScraper, ScrapingOutput } from "../../../interfaces";
import { PageManager } from "../handlers/PageManager";
import playwright, { Browser, Locator, Page } from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper";
import { generateValidUrl } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";
import { delay, runTasks } from "../../../util/promiseUtil";

const DATE_SELECT = "#cc_lineup_select_dates";
const DATE_OPTIONS = "div.header > div > select > option";
const SHOW_CONTAINER = "#lineup_sets > div";
const DATE_TIME = "span.bold";
const COMEDIAN_NAME = "span.name";
const SHOW_NAME = "span.title";
const TICKET_LINK = "div.make-reservation > a";
const PRICE = "ul.ccgrf-list > li.selected > p.cover"

export class ComedyCellar implements ClubScraper {

  private clubData: ClubScrapingData;
  private browser: Browser;
  private pageManager = new PageManager();
  private scraper = new ShowScraper();

  constructor(clubData: ClubScrapingData, browser: playwright.Browser) {
    this.clubData = clubData;
    this.browser = browser;
  }

  getAllDateOptions = async (page: Page): Promise<string[]> => {
    const locator = page.locator(DATE_OPTIONS);
    return this.pageManager.getValues(locator)
  }

  scrape = async (): Promise<ScrapingOutput[]> => {
    return this.browser.newPage()
      .then((page: Page) => this.pageManager.navigateToUrl(page, this.clubData.schedulePageUrl))
      .then((page: Page) => this.runClubScrapingFunction(page))
      .catch((error) => {
        console.log(`Error scraping Comedy Cellar: ${error}`)
        return []
      })
  }

  runClubScrapingFunction = async (page: Page): Promise<ScrapingOutput[]> => {
    return this.getAllDateOptions(page)
      .then((links: string[]) => this.runDateLoop(page, links))
  }

  runDateLoop = async (page: Page, dates: string[]): Promise<ScrapingOutput[]> => {
    var scrapedShows: ScrapingOutput[] = []

    for (let index = 0; index < dates.length - 1; index++) {
      const date = dates[index];
      const shows = await this.selectDateAndScrape(page, date)
      scrapedShows.push(...shows)
    }

    await this.browser.close()
    return scrapedShows
  }

  selectDateAndScrape = async (page: Page, date: string): Promise<ScrapingOutput[]> => {
    const dateSelectorLocator = page.locator(DATE_SELECT);
    return this.pageManager.selectDateOption(dateSelectorLocator, date)
      .then(() => delay(2000))
      .then(() => this.scrapePageContents(page, date))
  }

  scrapePageContents = async (page: Page, date: string) => {
    return page.locator(SHOW_CONTAINER).all()
      .then((containers: Array<Locator>) => {
        const tasks = containers.map((locator: Locator) => this.scrapeContainer(locator))
        return runTasks(tasks)
      })
      .then((scrapingOutput: any[]) => this.getPrices(scrapingOutput))
      .then((scrapingOutput: any[]) => scrapingOutput.map((output: any) => this.processOutput(output, date)))
  }

  scrapeContainer = async (container: Locator): Promise<any> => {
    return this.scraper.scrape({
      comedianNameLocator: container.locator(COMEDIAN_NAME),
      dateTimeLocator: container.locator(DATE_TIME),
      ticketLinkLocator: container.locator(TICKET_LINK),
      showNameLocator: container.locator(SHOW_NAME)
    })
  }

  getPrices = async (output: any[]): Promise<any[]> => {
    var scrapedShows: any[] = []
    const newPage = await this.browser.newPage();

    for (let index = 0; index < output.length - 1; index++) {
      const show = output[index];
      const link = generateValidUrl(this.clubData.baseUrl, show[2])
      show[4] = await this.navToTicketAndScrape(newPage, link)
      scrapedShows.push(show)
    }
    newPage.close()
    return scrapedShows
  }

  navToTicketAndScrape = async (page: Page, link: string): Promise<string> => {
    return this.pageManager.navigateToUrl(page, link)
      .then((page: Page) => {
        const locator = page.locator(PRICE)
        return this.scraper.getPrice(locator)
      })
  }

  processOutput = (output: any[], date: string): ScrapingOutput => {

    const show = new Show({
      lineup: output[0],
      dateTime: new DateTimeContainer(output[1]).asDateObject(),
      ticketLink: generateValidUrl(this.clubData.baseUrl, output[2]),
      name: output[3],
      price: output[4],
      clubId: this.clubData.id,
    })

    show.overrideDate(date)

    return {
      show: show.asCreateShowDTO(),
      comedians: show.asCreateComedianDTOArray()
    } as ScrapingOutput
  }

}