import puppeteer from "puppeteer";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { ElementScaper } from "./ElementScaper.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { ClubHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { delay } from "../util/types/promiseUtil.js";
import { LINKS } from "../constants/links.js";
import { Club } from "../classes/Club.js";
import { Comedian } from "../classes/Comedian.js";

export class ClubScraper {

  private club: Club;
  private json: any;
  private browser: puppeteer.Browser;
  private comedianScraper: ComedianScraper;
  private elementScraper = new ElementScaper();

  constructor(club: Club,
    json: any,
    browser: puppeteer.Browser,
    comedianScraper: ComedianScraper,
  ) {
    this.club = club;
    this.browser = browser;
    this.json = json;
    this.comedianScraper = comedianScraper;
  }

  // #region Computed variables
  private getClubHtmlConfig = (): ClubHTMLConfiguration => {
    return this.json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.clubConfig];
  }

  private shouldScrapeByDates = () => {
    return this.getClubHtmlConfig().shouldScapeByDates;
  }

  private shouldScrapeByShows = () => {
    return this.getClubHtmlConfig().shouldScrapeByShows;
  }
  // #endregion

  // #region Element selectors
  private dateOptionsSelector = () => {
    return this.getClubHtmlConfig().dateOptionsSelector ?? "";
  }

  private dateMenuSelector = () => {
    return this.getClubHtmlConfig().dateMenuSelector ?? "";
  }

  private allShowElementsSelector = () => {
    return this.getClubHtmlConfig().allShowElementsSelector ?? "";
  }

  private allShowLinksSelector = () => {
    return this.getClubHtmlConfig().allShowLinksSelector ?? "";
  }
  // #endregion

  // #region Element getters
  getAllShowElementHandlers = async (page: puppeteer.Page): Promise<puppeteer.ElementHandle<Element>[]> => {
    return this.elementScraper.getElementHandlers(page, this.allShowElementsSelector())
  }

  getAllDates = async (page: puppeteer.Page): Promise<string[]> => {
    return this.elementScraper.getValuesFromAllElements(page, this.dateOptionsSelector())
  }

  getAllShowDetailLinks = async (page: puppeteer.Page): Promise<string[]> => {
    return this.elementScraper.getElementCount(page, this.allShowLinksSelector())
      .then((count: number) => count > 0 ? this.elementScraper.getHrefFromAllElements(page, this.allShowLinksSelector()) : [])
      .then((links: string[]) => links.filter((link: string) => !LINKS.badLinks.includes(link)))
  }
  // #endregion

  // #region Task getters
  getPageScrapingTasks = async (basePage: puppeteer.Page): Promise<Comedian[]> => {
    console.log(`Started scraping ${this.club.getName()} at ${new Date()}`);

    if (this.shouldScrapeByDates()) return this.scrapeByDates(basePage)
    else if (this.shouldScrapeByShows()) return this.scrapeByShowDetails(basePage)
    else return this.scrapePage(basePage)

  }
  // #endregion

  // #region Scrapers
  public scrape = async (): Promise<Comedian[]> => {
    return this.buildRootPage(this.club.getScrapedPage())
      .then((response: puppeteer.Page) => this.getPageScrapingTasks(response))
      .then((comedians: Comedian[]) => comedians);
  }

  private buildRootPage = async (destination: string): Promise<puppeteer.Page> => {
    return this.browser.newPage()
      .then((page: puppeteer.Page) => page.goto(destination).then(() => page));
  }

  scrapeByShowDetails = async (page: puppeteer.Page): Promise<Comedian[]> => {
    return this.getAllShowDetailLinks(page)
      .then((links: string[]) => this.scrapeAllTicketLinks(page, links))
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays));
  }

  scrapeAllTicketLinks = async (page: puppeteer.Page, links: string[]): Promise<Comedian[][]> => {
    var comedianArrays: Comedian[][] = [];

    for (const link of links) {
      const comedians = await this.navigateToUrlAndScrapePage(page, link)
      comedianArrays.push(comedians)
    }

    return comedianArrays
  }

  navigateToUrlAndScrapePage = async (page: puppeteer.Page, link: string): Promise<Comedian[]> => {
    const url = this.club.getBaseWebsite() + link;
    return page.goto(url)
      .then(() => delay(1000))
      .then(() => this.scrapePage(page, undefined, url))
  }

  scrapeByDates = async (page: puppeteer.Page): Promise<Comedian[]> => {
    return this.getAllDates(page)
      .then((dates: string[]) => this.scrapeAllDates(page, dates))
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays));
  }

  scrapeAllDates = async (page: puppeteer.Page, dates: string[]): Promise<Comedian[][]> => {
    var comedianArrays: Comedian[][] = [];

    for (const date of dates) {
      const comedians = await this.selectDateAndScrapePage(page, date)
      comedianArrays.push(comedians)
    }

    return comedianArrays
  }

  selectDateAndScrapePage = async (page: puppeteer.Page, date: string): Promise<Comedian[]> => {
    return page.select(this.dateMenuSelector(), date)
      .then(() => delay(1000))
      .then(() => this.scrapePage(page, date))
  }

  scrapePage = async (page: puppeteer.Page, date?: string, url?: string): Promise<Comedian[]> => {
    return this.getAllShowElementHandlers(page)
      .then((showElementHandlers: puppeteer.ElementHandle<Element>[]) => this.comedianScraper.scrapeComedians(showElementHandlers, date, url));
  }
  // #endregion

}