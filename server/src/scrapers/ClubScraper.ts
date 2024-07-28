import puppeteer from "puppeteer";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { ElementScaper } from "./ElementScaper.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { ClubHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { LINKS } from "../constants/links.js";
import { Club } from "../classes/Club.js";
import { Comedian } from "../classes/Comedian.js";
import { ElementInteractor } from "./ElementInteractor.js";
import { ProvidedScrapingValue } from "../types/providedScrapingValue.interface.js";


const INTERACTION_DELAY = 1000;

export class ClubScraper {

  private club: Club;
  private json: any;
  private browser: puppeteer.Browser;
  private comedianScraper: ComedianScraper;
  private elementScraper = new ElementScaper();
  private elementInteractor = new ElementInteractor();

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

  private requiresSelectingDates = () => {
    return this.getClubHtmlConfig().shouldScapeByDates;
  }

  private requiresNavigatingToShowLinks = () => {
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

  private expansionSelector = () => {
    return this.getClubHtmlConfig().expansionSelector ?? "";
  }
  // #endregion

  // #region Element getters
  getAllShowElementHandlers = async (page: puppeteer.Page): Promise<puppeteer.ElementHandle<Element>[]> => {
    return this.elementScraper.getElementHandlers(page, this.allShowElementsSelector())
  }

  getAllDateOptions = async (page: puppeteer.Page): Promise<string[]> => {
    return this.elementScraper.getValuesFromAllElements(page, this.dateOptionsSelector())
  }

  getAllShowLinks = async (page: puppeteer.Page): Promise<string[]> => {
    return this.elementScraper.getElementCount(page, this.allShowLinksSelector())
      .then((count: number) => count > 0 ? this.elementScraper.getHrefFromAllElements(page, this.allShowLinksSelector()) : [])
      .then((links: string[]) => links.filter((link: string) => !LINKS.badLinks.includes(link)))
  }
  // #endregion

  // #region Main logic
  public scrape = async (): Promise<Comedian[]> => {
    console.log(`Started scraping ${this.club.getName()} at ${new Date()}`);
    return this.buildRootPage(this.club.getScrapedPage())
      .then((response: puppeteer.Page) => this.elementInteractor.expandPage(response, this.expansionSelector()))
      .then((response: puppeteer.Page) => this.dispatchPageScrapingTasks(response))
      .then((comedians: Comedian[]) => comedians);
  }

  private buildRootPage = async (destination: string): Promise<puppeteer.Page> => {
    return this.browser.newPage()
      .then((page: puppeteer.Page) => page.goto(destination).then(() => page));
  }

  // #endregion

  // #region Scraping tasks
  dispatchPageScrapingTasks = async (basePage: puppeteer.Page): Promise<Comedian[]> => {
    if (this.requiresSelectingDates()) return this.scrapeByDates(basePage)
    else if (this.requiresNavigatingToShowLinks()) return this.scrapeByShowLinks(basePage)
    else return this.scrapeCurrentPage(basePage)
  }
  // #endregion

  private scrapeByShowLinks = async (page: puppeteer.Page): Promise<Comedian[]> => {
    return this.getAllShowLinks(page)
      .then((links: string[]) => this.scrapeAllTicketLinks(page, links))
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays))
  }

  scrapeAllTicketLinks = async (page: puppeteer.Page, links: string[]): Promise<Comedian[][]> => {
    var comedianArrays: Comedian[][] = [];

    for (const link of links) {
      const url = this.club.getBaseWebsite() + link;
      const comedians = await this.navigateToUrlAndScrapePage(page, url)
      comedianArrays.push(comedians)
    }

    return comedianArrays
  }

  navigateToUrlAndScrapePage = async (page: puppeteer.Page, url: string): Promise<Comedian[]> => {
    return this.elementInteractor.navigateToUrl(url, page, INTERACTION_DELAY)
      .then(() => this.scrapeCurrentPage(page, {ticketUrl: url}))
  }

  scrapeByDates = async (page: puppeteer.Page): Promise<Comedian[]> => {
    return this.getAllDateOptions(page)
      .then((dateOptions: string[]) => this.loopThroughDateOptions(page, dateOptions))
      .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays));
  }

  loopThroughDateOptions = async (page: puppeteer.Page, dateOptions: string[]): Promise<Comedian[][]> => {
    var comedianArrays: Comedian[][] = [];

    for (const dateOption of dateOptions) {
      const comedians = await this.selectDateOptionAndScrapePage(page, dateOption)
      comedianArrays.push(comedians)
    }

    return comedianArrays
  }

  selectDateOptionAndScrapePage = async (page: puppeteer.Page, dateOption: string): Promise<Comedian[]> => {
    return this.elementInteractor.selectOption(dateOption, this.dateMenuSelector(), page, INTERACTION_DELAY)
      .then(() => this.scrapeCurrentPage(page, {date: dateOption}))
  }

  scrapeCurrentPage = async (page: puppeteer.Page, providedScrapingValues?: ProvidedScrapingValue): Promise<Comedian[]> => {
    return this.getAllShowElementHandlers(page)
      .then((showElementHandlers: puppeteer.ElementHandle<Element>[]) => this.comedianScraper.scrapeComedians(showElementHandlers, providedScrapingValues));
  }
  // #endregion

}