import playwright from "playwright-core";
import { PageManager } from "./PageManager.js";
import { Show } from "./Show.js";
import { writeLogToFile } from "../util/logUtil.js";
import { generateScrapingLoop } from "../util/scraperUtil.js";
import { ClubScrapingData } from "./interfaces/club.interface.js";
import { processShowsForStorage } from "../util/domainModels/show/showUtil.js";
import { ScraperType } from "./@types/ScraperType.js";
import { Scrapable, ScrapingOutput } from "./interfaces/scrape.interface.js";

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
    .then(() => processShowsForStorage(this.clubData, shows as Show[]));
  }

  runClubScrapingFunction = async (page: playwright.Page): Promise<Show[]> => { 
    switch (this.clubData.scrapingConfig.type) {
      
      case ScraperType.A: return this.selectDateOptionAndScrape(page)
      case ScraperType.B: return this.expandPageGoToDetailPageAndScrape(page)
      case ScraperType.C: return this.goToDetailPageAndScrape(page)
      case ScraperType.D: return this.runPaginatedDetailPageLoop(page)
      default: throw new Error("No scraping type found")
    }
  }

  expandPageGoToDetailPageAndScrape = async (scrapable: Scrapable): Promise<Show[]> => {
    return this.pageManager.expandPage(scrapable as playwright.Page)
    .then(page => this.goToDetailPageAndScrape(page))
  }

  selectDateOptionAndScrape = async (scrapable: Scrapable): Promise<Show[]> => {
    return generateScrapingLoop(scrapable as playwright.Page,
      this.pageManager.getAllDateOptions,
      this.pageManager.selectDateOption,
      this.pageManager.scrapeContainers
    )
  }

  goToDetailPageAndScrape = async (scrapable: Scrapable): Promise<Show[]> => {
    return generateScrapingLoop(scrapable as playwright.Page,
      this.pageManager.getValidDetailPageLinks,
      this.pageManager.navigateToUrl,
      this.pageManager.scrapeDetailPage
    )
  }

  runPaginatedDetailPageLoop = async (page: playwright.Page): Promise<Show[]> => {
    return generateScrapingLoop(page,
      this.pageManager.getAllPageLinks,
      this.pageManager.navigateToUrl,
      this.goToDetailPageAndScrape
    )
  }

}
