import playwright from "playwright";
import { PageManager } from "./PageManager.js";
import { ScraperType } from "../../@types/ScraperType.js";
import { generateScrapingLoop } from "../../util/scraperUtil.js";
import { Scrapable } from "../../api/interfaces/scrapable.interface.js";
import { ClubInterface } from "../../api/interfaces/club.interface.js";
import { ShowInterface } from "../../api/interfaces/show.interface.js";
import { Show } from "../../classes/Show.js";

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
  
  public scrape = async (): Promise<Show[]> => {
    console.log(`Started scraping ${this.club.name} at ${new Date()}`);

    return this.browser.newPage()
      .then((page: playwright.Page) => this.pageManager.navigateToUrl(page, this.club.schedulePageUrl))
      .then((page: playwright.Page) => this.runClubScrapingFunction(page))
      .then((shows: ShowInterface[]) => this.closeBrowserAndReturnShows(shows))
  }

  private closeBrowserAndReturnShows = async (shows: ShowInterface[]) => {
    return this.browser.close()
    .then(() => {
      const showModels = shows as Show[]
      showModels.forEach(showModel => showModel.setClub(this.club))
      return showModels.filter(showModel => showModel.isValid)
    })
  }

  runClubScrapingFunction = async (page: playwright.Page): Promise<ShowInterface[]> => { 
    switch (this.club.scrapingConfig.type) {
      
      case ScraperType.A: return this.selectDateOptionAndScrape(page)
      case ScraperType.B: return this.expandPageGoToDetailPageAndScrape(page)
      case ScraperType.C: return this.goToDetailPageAndScrape(page)
      case ScraperType.D: return this.runPaginatedDetailPageLoop(page)
      default: throw new Error("No scraping type found")
    }
  }

  expandPageGoToDetailPageAndScrape = async (scrapable: Scrapable): Promise<ShowInterface[]> => {
    return this.pageManager.expandPage(scrapable as playwright.Page)
    .then(page => this.goToDetailPageAndScrape(page))
  }

  selectDateOptionAndScrape = async (scrapable: Scrapable): Promise<ShowInterface[]> => {
    return generateScrapingLoop(scrapable as playwright.Page,
      this.pageManager.getAllDateOptions,
      this.pageManager.selectDateOption,
      this.pageManager.scrapeContainers
    )
  }

  goToDetailPageAndScrape = async (scrapable: Scrapable): Promise<ShowInterface[]> => {
    return generateScrapingLoop(scrapable as playwright.Page,
      this.pageManager.getValidDetailPageLinks,
      this.pageManager.navigateToUrl,
      this.pageManager.scrapeDetailPage
    )
  }

  runPaginatedDetailPageLoop = async (page: playwright.Page): Promise<ShowInterface[]> => {
    return generateScrapingLoop(page,
      this.pageManager.getAllPageLinks,
      this.pageManager.navigateToUrl,
      this.goToDetailPageAndScrape
    )
  }

}
