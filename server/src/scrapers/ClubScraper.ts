import puppeteer from "puppeteer";
import { ElementScaper } from "./ElementScaper.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { Club } from "../classes/Club.js";
import { Comedian } from "../classes/Comedian.js";
import { PageHandler } from "./PageHandler.js";
import { ShowScraper } from "./ShowScraper.js";
import { ShowContainerScraper } from "./ShowContainerScraper.js";

const INTERACTION_DELAY = 1000;

export class ClubScraper {

  private club: Club;
  private browser: puppeteer.Browser;
  private showScraper: ShowScraper;
  private pageHandler = new PageHandler();
  private elementScraper = new ElementScaper();
  private showContainerScraper = new ShowContainerScraper();

  constructor(club: Club,
    browser: puppeteer.Browser  
  ) {
    this.club = club;
    this.browser = browser;
    this.showScraper = new ShowScraper(club);
  }

  // #endregion

  // #region Main logic
  public scrape = async (): Promise<Comedian[]> => {
    console.log(`Started scraping ${this.club.name} at ${new Date()}`);
  
    return this.pageHandler.buildRootPage(this.browser, this.club.scrapedPage)
    .then((basePage: puppeteer.Page) => this.pageHandler.expandPageIfPossible(basePage, this.club.clubConfig.moreShowsSelector))
    .then((expandedBasePage: puppeteer.Page) => this.dispatchPageScrapingTasks(expandedBasePage))
    .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays))
    
  }
  // #endregion

  // #region Scraping tasks
  dispatchPageScrapingTasks = async (basePage: puppeteer.Page): Promise<Comedian[][]> => {

    if (this.club.clubConfig.shouldScapeByDates) {
      return this.elementScraper.getAllValuesFrom(basePage, this.club.clubConfig.dateOptionsSelector)
      .then((dateOptions: string[]) => this.scrapeByDateOptions(basePage, dateOptions))
    }

    else if (this.club.clubConfig.shouldScrapeByShowDetails) {
      return this.showContainerScraper.getShowDetailPageLinks(basePage, 
        this.club.clubConfig.showContainerSelector, 
        this.club.clubConfig.validShowContainerSignifier,
        this.club.clubConfig.showDetailPageLinkSelector, 
      )
      .then((urls: string[]) => this.scrapeByUrls(basePage, urls))
    }

    return this.showScraper.scrapeAllShows(basePage)

  }
  // #endregion

  scrapeByDateOptions = async (page: puppeteer.Page, dateOptions: string[]): Promise<Comedian[][]> => {

    var comedianArrays: Comedian[][] = [];

    for (const dateOption of dateOptions) {
      const comedians = await this.selectDateOptionAndScrapePage(page, dateOption)
      comedianArrays = comedianArrays.concat(comedians)
    }

    return comedianArrays
  }

  private scrapeByUrls = async (page: puppeteer.Page, urls: string[]): Promise<Comedian[][]> => {
    var comedianArrays: Comedian[][] = [];

    for (const url of urls) {
      const completeUrl = this.club.baseWebsite + url;
      const comedians = await this.navigateToUrlAndScrapePage(page, completeUrl)
      comedianArrays.push(comedians)
    }

    return comedianArrays
  }

  navigateToUrlAndScrapePage = async (page: puppeteer.Page, url: string): Promise<Comedian[]> => {
    return this.pageHandler.navigateToUrl(url, page, INTERACTION_DELAY)
      .then(() => {
        console.log(`Scraping show at ${url}`)
        return this.showScraper.scrapeShow(page, {ticketUrl: url})
      })
  }

  selectDateOptionAndScrapePage = async (page: puppeteer.Page, dateOption: string): Promise<Comedian[][]> => {    
    return this.pageHandler.selectOption(page, INTERACTION_DELAY, dateOption, this.club.clubConfig.dateMenuSelector)
      .then(() => this.showScraper.scrapeAllShows(page, {date: dateOption}))
  }

}