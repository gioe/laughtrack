import puppeteer from "puppeteer";
import { ScraperInterface } from "../types/scraper.interface.js";
import { ClubHTMLConfiguration, DatesHTMLConfiguration, HTMLConfigurable } from "../types/htmlconfigurable.interface.js";
import { Club } from "./Club.js";
import { Comedian } from "./Comedian.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { Logger } from "./Logger.js";
import { Scraper } from "./Scraper.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { flattenElements } from "../util/types/arrayUtil.js";

export class ScrapingManager implements ScraperInterface {
  scrapedPage: string;
  private scraper: Scraper;
  private comedianScraper: ComedianScraper;
  private clubConfig: ClubHTMLConfiguration;
  private dateConfig: DatesHTMLConfiguration;
  private club: Club;
  private browser: puppeteer.Browser;
  private logger: Logger;

  constructor(jsonModel: any, browser: puppeteer.Browser, logger: Logger) {
    this.browser = browser;
    this.scrapedPage = jsonModel[SCRAPER_KEYS.scrapedPage]
    this.clubConfig = jsonModel[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.clubConfig]
    this.dateConfig = jsonModel[SCRAPER_KEYS.scrapedPage][SCRAPER_KEYS.dateConfig]
    this.comedianScraper = new ComedianScraper(logger, jsonModel)
    this.club = new Club(jsonModel);
    this.scraper = new Scraper(logger, this.scrapedPage)
    this.logger = logger
  }

  // #region Computed booleans
  private shouldNavigateDates = () => {
    return this.dateConfig != undefined;
  }
  // #endregion

  // #region Element selectors
  private dateOptionsSelector = () => {
    return this.dateConfig.dateOptionsSelector ?? "";
  }

  private dateMenuSelector = () => {
    return this.dateConfig.dateMenuSelector ?? "";
  }

  private allShowsSelector = () => {
    return this.clubConfig.allShowsSelector ?? "";
  }

  // #endregion

  // #region Element getters
  getAllShowElementHandlers = async (page: puppeteer.Page): Promise<puppeteer.ElementHandle<Element>[]> => {

    return this.scraper.getElementHandlers(page, this.allShowsSelector())
  }

  getAllDates = async (page: puppeteer.Page): Promise<string[]> => {
    return this.scraper.getTextValuesFromAllElements(page, this.dateOptionsSelector())
  }

  // #endregion

  // #region Task getters
  getPageScrapingTasks = async (basePage: puppeteer.Page, club: Club): Promise<Comedian[]> => {
    this.log(`Started scraping ${basePage.url()}`);

    if (this.shouldNavigateDates()) {
      return this.scrapePageTree(basePage, club)
    } else {
      return this.scrapePage(basePage, club)
    }
  }

  // #endregion

  // #region Scrapers
  public scrape = async (): Promise<Comedian[]> => {
    return this.scrapeClub(this.club)
      .then((comedians: Comedian[]) => {

        comedians.forEach(comedian => this.log(comedian.name))
        return comedians
  });
  }

  scrapeClub = async (club: Club) => {
    this.log(`Started scraping ${club.name} at ${new Date()}`);

    return this.generatePageAndNavigateToRoot(club.scrapedPage)
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
        return this.comedianScraper.scrapeComedians(showElementHandlers, club, date)
      });
  }
  // #endregion

  // #region Logger
  log = (input: any) => {
    this.logger.log(this.scraper.scrapedPage, input)
  }
  // #endregion

}