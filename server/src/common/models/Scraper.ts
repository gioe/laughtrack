import playwright from "playwright-core";
import { PageManager } from "./PageManager.js";
import { Show } from "./Show.js";
import { writeLogToFile } from "../util/logUtil.js";
import { CreateShowDTO } from "../interfaces/data/show.interface.js";
import { processShowsForStorage } from "../util/showUtil.js";
import { ScraperType } from "../@types/ScraperType.js";
import { Scrapable } from "../interfaces/client/scrapable.interface.js";
import { generateScrapingLoop } from "../util/scraperUtil.js";
import { ClubInterface } from "../interfaces/client/club.interface.js";

export class Scraper {

  private club: ClubInterface;
  private browser: playwright.Browser;
  private pageManager: PageManager;

  constructor(club: ClubInterface,
    browser: playwright.Browser,
  ) {
    this.club = club;
    this.browser = browser;
    this.pageManager = new PageManager(club.scrapingConfig);
  }
  
  public scrape = async (): Promise<CreateShowDTO[]> => {
    writeLogToFile(`Started scraping ${this.club.name} at ${new Date()}`)

    return this.browser.newPage()
      .then((page: playwright.Page) => this.pageManager.navigateToUrl(page, this.club.schedulePageUrl))
      .then((page: playwright.Page) => this.runClubScrapingFunction(page))
      .then((shows: Show[]) => this.closeBrowserAndReturnShows(shows))
  }

  private closeBrowserAndReturnShows = async (shows: Show[]): Promise<CreateShowDTO[]> => {
    return this.browser.close()
    .then(() => processShowsForStorage(this.club, shows as Show[]));
  }

  runClubScrapingFunction = async (page: playwright.Page): Promise<Show[]> => { 
    switch (this.club.scrapingConfig.type) {
      
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
