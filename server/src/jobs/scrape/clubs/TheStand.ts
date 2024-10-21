import { Show } from "../../../common/models/classes/Show.js";
import { ClubScrapingData } from "../../../common/models/interfaces/club.interface.js";
import { ClubScraper, ScrapingOutput } from "../../../common/models/interfaces/scrape.interface.js";
import { PageManager } from "../handlers/PageManager.js";
import playwright, { Locator, Page, Browser} from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper.js";
import { runTasks } from "../../../common/util/promiseUtil.js";
import { generateValidUrl } from "../../../common/util/primatives/urlUtil.js";
import { DateTimeContainer } from "../containers/DateTimeContainer.js";

const MORE = "div.row.moreitems.dark-links.my-5 > div > div > a";
const SHOW_CONTAINER = "div.row.show_row";
const DATE_TIME = "span.show_date";
const COMEDIAN_NAME = "div.col-4.col-md-3.col-xl-2.lineup-item";
const SHOW_NAME = "h2.showtitle";
const TICKET_LINK = "div.d-grid.gap-2 > a";
const PRICE = "div.price";
const SEPARATOR =  ",";

export class TheStand implements ClubScraper {

  private clubData: ClubScrapingData;
  private browser: Browser;
  private pageManager = new PageManager();
  private scraper = new ShowScraper();

  constructor(clubData: ClubScrapingData, browser: playwright.Browser) {
    this.clubData = clubData;
    this.browser = browser;
  }

  scrape = async (): Promise<ScrapingOutput[]> => {
    return this.browser.newPage()
      .then((page: Page) => this.pageManager.navigateToUrl(page, this.clubData.schedulePageUrl))
      .then((page: Page) => this.runClubScrapingFunction(page))
      .catch((error) => {
        console.log(`Error scraping The Stand: ${error}`)
        return []
      })
  }

  runClubScrapingFunction = async (page: Page): Promise<ScrapingOutput[]> => {
    const moreLocator = page.locator(MORE);
    return this.pageManager.expandPage(page, moreLocator)
      .then(page => page.locator(SHOW_CONTAINER).all())
      .then((containers: Array<playwright.Locator>) => {
        const tasks = containers.map((value: Locator) => this.scrapeContainer(value))
        return runTasks(tasks)
      })
      .then((output: ScrapingOutput[]) => {
        this.browser.close();
        return output
      })
  }

  scrapeContainer = async (container: Locator): Promise<ScrapingOutput> => {
    return this.scraper.scrape({
      comedianNameLocator: container.locator(COMEDIAN_NAME),
      dateTimeLocator: container.locator(DATE_TIME),
      ticketLinkLocator: container.locator(TICKET_LINK),
      showNameLocator: container.locator(SHOW_NAME),
      priceLocator: container.locator(PRICE),
    })
    .then((scrapingOutput: any[]) => this.processOutput(scrapingOutput))
  }

  processOutput = async  (output: any[]): Promise<ScrapingOutput> => {
    const show = new Show({
      lineup: output[0],
      dateTime: new DateTimeContainer(output[1], SEPARATOR).asDateObject(),
      ticketLink: generateValidUrl(this.clubData.baseUrl, output[2]),
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