import playwright from "playwright";
import { PageManager } from "./PageManager.js";
import { ScraperType } from "../../types/ScraperType.js";
import { generateScrapingLoop } from "../../util/scraperUtil.js";
import { Scrapable } from "../../api/interfaces/scrapable.interface.js";
import { Club } from "../../api/interfaces/club.interface.js";
import { Show } from "../../api/interfaces/show.interface.js";
import { ShowModel } from "../../classes/ShowModel.js";

export class Scraper {

  private club: Club;
  private browser: playwright.Browser;
  private pageManager: PageManager;

  constructor(club: Club,
    browser: playwright.Browser,
  ) {
    this.club = club;
    this.browser = browser;
    this.pageManager = new PageManager(club.scrapingConfig);
  }
  
  public scrape = async (): Promise<ShowModel[]> => {
    console.log(`Started scraping ${this.club.name} at ${new Date()}`);

    return this.browser.newPage()
      .then((page: playwright.Page) => this.pageManager.navigateToUrl(page, this.club.schedulePageUrl))
      .then((page: playwright.Page) => this.runClubScrapingFunction(page))
      .then((shows: Show[]) => {
        const showModels = shows as ShowModel[]
        showModels.forEach(showModel => showModel.setClub(this.club))
        return showModels
      }
    )

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
