import puppeteer from "puppeteer";
import { Club } from "./Club.js";
import { Comedian } from "./Comedian.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { Logger } from "./Logger.js";
import { ElementScaper } from "./ElementScaper.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { ClubHTMLConfiguration } from "../types/htmlconfigurable.interface.js";

export class ClubScraper {

  private club: Club;
  private json: any;
  private browser: puppeteer.Browser;
  private elementScraper: ElementScaper;
  private comedianScraper: ComedianScraper;
  private logger: Logger;

  constructor(club: Club,
    json: any,
    browser: puppeteer.Browser,
    elementScraper: ElementScaper,
    comedianScraper: ComedianScraper,
    logger: Logger
  ) {
    this.club = club;
    this.browser = browser;
    this.json = json;
    this.elementScraper = elementScraper;
    this.comedianScraper = comedianScraper;
    this.logger = logger;
  }

  // #region Computed variables
  private shouldNavigateDates = () => {
    return this.getClubHtmlConfig().dateMenuSelector != undefined;
  }

  private getClubHtmlConfig = (): ClubHTMLConfiguration => {
    return this.json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.clubConfig];
  }

  // #endregion

  // #region Element selectors
  private dateOptionsSelector = () => {
    return this.getClubHtmlConfig().dateOptionsSelector ?? "";
  }

  private dateMenuSelector = () => {
    return this.getClubHtmlConfig().dateMenuSelector ?? "";
  }

  private allShowsSelector = () => {
    return this.getClubHtmlConfig().allShowsSelector ?? "";
  }

  // #endregion

  // #region Element getters
  getAllShowElementHandlers = async (page: puppeteer.Page): Promise<puppeteer.ElementHandle<Element>[]> => {
    return this.elementScraper.getElementHandlers(page, this.allShowsSelector())
  }

  getAllDates = async (page: puppeteer.Page): Promise<string[]> => {
    return this.elementScraper.getTextValuesFromAllElements(page, this.dateOptionsSelector())
  }

  // #endregion

  // #region Task getters
  getPageScrapingTasks = async (basePage: puppeteer.Page, club: Club): Promise<Comedian[]> => {
    this.log(`Started scraping ${club.getName()} at ${new Date()}`);
    return this.shouldNavigateDates() ? this.scrapePageTree(basePage, club) : this.scrapePage(basePage, club)
  }

  // #endregion

  // #region Scrapers
  public scrape = async (): Promise<Comedian[]> => {
    return this.scrapeClub(this.club)
      .then((comedians: Comedian[]) => comedians);
  }

  scrapeClub = async (club: Club) => {
    return this.generatePageAndNavigateToRoot(club.getScrapedPage())
      .then((response: puppeteer.Page) => this.getPageScrapingTasks(response, club));
  }

  private generatePageAndNavigateToRoot = async (destination: string): Promise<puppeteer.Page> => {
    return this.browser.newPage()
      .then((page: puppeteer.Page) => page.goto(destination).then(() => page));
  }

  scrapePageTree = async (page: puppeteer.Page, club: Club): Promise<Comedian[]> => {
    return this.getAllDates(page)
      .then((dates: string[]) => this.scrapeAllDates(page, club, dates))
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays));
  }

  scrapeAllDates = async (page: puppeteer.Page, club: Club, dates: string[]): Promise<Comedian[][]> => {
    var comedianArrays: Comedian[][] = [];

    for (const date of dates) {
      const comedians = await this.selectDateAndScrapePage(page, club, date)
      comedianArrays.push(comedians)
    }

    return comedianArrays
  }

  selectDateAndScrapePage = async (page: puppeteer.Page, club: Club, date: string): Promise<Comedian[]> => {
    return page.select(this.dateMenuSelector(), date)
      .then(() => this.scrapePage(page, club, date))
  }

  scrapePage = async (page: puppeteer.Page, club: Club, date?: string): Promise<Comedian[]> => {
    return this.getAllShowElementHandlers(page)
      .then((showElementHandlers: puppeteer.ElementHandle<Element>[]) => {
        this.log(`Found ${showElementHandlers.length} shows to scrape`);
        return this.comedianScraper.scrapeComedians(showElementHandlers, club, date)
      });
  }
  // #endregion

  // #region Logger
  log = (input: any) => {
    this.logger.log(this.club.getScrapedPage(), input)
  }
  // #endregion

}