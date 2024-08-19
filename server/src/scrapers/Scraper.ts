import playwright from "playwright";
import { Club } from "../classes/Club.js";
import { Comedian } from "../classes/Comedian.js";
import { PageManager } from "./PageManager.js";
import { InteractionConfig } from "../classes/InteractionConfig.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { ScraperType } from "../types/scraperTypes.js";
import { generateScrapingLoop } from "../util/types/scraperUtil.js";
import { Scrapable } from "../types/scrapable.interface.js";

export class Scraper {

  private club: Club;
  private browser: playwright.Browser;
  private pageManager: PageManager;
  private interactionConfig: InteractionConfig;

  constructor(json: any,
    browser: playwright.Browser,
    pageManager: PageManager,
    interactionConfig: InteractionConfig
  ) {
    this.club = new Club(json);
    this.browser = browser;
    this.pageManager = pageManager;
    this.interactionConfig = interactionConfig;
  }
  
  public scrape = async (): Promise<Comedian[]> => {
    console.log(`Started scraping ${this.club.name} at ${new Date()} with scraper of type ${this.interactionConfig.scraperType}`);

    return this.browser.newPage()
      .then((page: playwright.Page) => this.pageManager.navigateToUrl(page, this.club.schedulePageUrl))
      .then((page: playwright.Page) => this.runClubScrapingFunctions(page))
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays))
  }

  runClubScrapingFunctions = async (page: playwright.Page): Promise<Comedian[][]> => { 
    switch (this.interactionConfig.scraperType) {
      
      case ScraperType.A: return this.selectDateOptionAndScrape(page)
      case ScraperType.B: return this.pageManager.expandPage(page).then(page => this.goToDetailPageAndScrape(page))
      case ScraperType.C: return this.goToDetailPageAndScrape(page)
      case ScraperType.D: return this.runPaginatedDetailPageLoop(page)

      default: throw new Error("No scraping type found")
    }
  }

  selectDateOptionAndScrape = async (scrapable: Scrapable) => {
    return generateScrapingLoop(scrapable as playwright.Page,
      this.pageManager.getAllDateOptions,
      this.pageManager.selectDateOption,
      this.pageManager.scrapeContainers
    )
  }

  goToDetailPageAndScrape = async (scrapable: Scrapable) => {
    return generateScrapingLoop(scrapable as playwright.Page,
      this.pageManager.getValidDetailPageLinks,
      this.pageManager.navigateToUrl,
      this.pageManager.scrapeDetailPage
    )
  }

  runPaginatedDetailPageLoop = async (page: playwright.Page) => {
    return generateScrapingLoop(page,
      this.pageManager.getAllPageLinks,
      this.pageManager.navigateToUrl,
      this.goToDetailPageAndScrape
    )
  }

}
