import playwright from "playwright-core";
import { PageManager } from "./PageManager.js";
import { Show } from "../../../common/models/classes/Show.js";
import { writeLogToFile } from "../../../common/util/logUtil.js";
import { generateScrapingLoop } from "../../../common/util/scraperUtil.js";
import { ClubScrapingData } from "../../../common/models/interfaces/club.interface.js";
import { processShowsForStorage } from "../../../common/util/domainModels/show/showUtil.js";
import { ScraperType } from "../../../common/models/@types/ScraperType.js";
import { ScrapingOutput } from "../../../common/models/interfaces/scrape.interface.js";

export class Scraper {

  private clubData: ClubScrapingData;
  private browser: playwright.Browser;
  private pageManager: PageManager;

  constructor(clubData: ClubScrapingData,
    browser: playwright.Browser,
  ) {
    this.clubData = clubData;
    this.browser = browser;
    this.pageManager = new PageManager(clubData.scrapingConfig);
  }

  public scrape = async (): Promise<ScrapingOutput[]> => {
    writeLogToFile(`Started scraping ${this.clubData.name} at ${new Date()}`)

    return this.browser.newPage()
      .then((page: playwright.Page) => this.pageManager.navigateToUrl(page, this.clubData.schedulePageUrl))
      .then((page: playwright.Page) => this.runClubScrapingFunction(page))
      .then((shows: Show[]) => this.closeBrowserAndProcess(shows))
  }

  private closeBrowserAndProcess = async (shows: Show[]): Promise<ScrapingOutput[]> => {
    return this.browser.close()
      .then(() => processShowsForStorage(this.clubData, shows));
  }

  runClubScrapingFunction = async (page: playwright.Page): Promise<Show[]> => {
    switch (this.clubData.scrapingConfig.type) {

      case ScraperType.A: return this.selectDateOptionAndScrape(page)
      case ScraperType.B: return this.getAllLinksAndScrape(page)
      case ScraperType.C: return this.runPaginatedDetailPageLoop(page)
      default: throw new Error("No scraping type found")
    }
  }

  selectDateOptionAndScrape = async (page: playwright.Page): Promise<Show[]> => {
    return generateScrapingLoop(page as playwright.Page,
      this.pageManager.getAllDateOptions,
      this.pageManager.selectDateOption,
      this.pageManager.scrapeDetailPage)
  }

  getAllLinksAndScrape = async (page: playwright.Page): Promise<Show[]> => {
    return this.pageManager.expandPage(page)
      .then(page => {
        return generateScrapingLoop(page,
          this.pageManager.getAllLinksOnPage,
          this.pageManager.navigateToUrl,
          this.pageManager.scrapeDetailPage)
      })
  }

  runPaginatedDetailPageLoop = async (page: playwright.Page): Promise<Show[]> => {
    return generateScrapingLoop(page,
      this.pageManager.getLinksAcrossPages,
      this.pageManager.navigateToUrl,
      this.pageManager.scrapeDetailPage)
  }

}
