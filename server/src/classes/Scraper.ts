import puppeteer from "puppeteer";
import { ScraperInterface } from "../types/scraper.interface.js";
import { HTMLConfigurable } from "../types/htmlconfigurable.interface.js";
import { Club } from "./Club.js";
import { Comedian } from "./Comedian.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { Logger } from "../util/logger.js";
import { Show } from "../types/show.interface.js";

import {
  emptyStringPromise,
  runTasks
} from "../util/types/promiseUtil.js";

import {
  getElementHandlers,
  getHrefFromSingeElement,
  getTextValueFromSingleElement,
  getTextValuesFromAllElements
} from "../util/puppeteer/puppeteerUtils.js";

import {
  buildShowFromScrapedElements
} from "../util/types/showUtil.js";

import {
  buildComedianFromScrapedElements,
  flattenComedians,
} from "../util/types/comedianUtil.js";

import { TextConfigurable } from "../types/textConfigurable.interface.js";

export class Scraper implements ScraperInterface {
  private logger = new Logger("https://comicstriplive.com/");
  public baseWebsite: string;
  private htmlConfig: HTMLConfigurable;
  private textConfig: TextConfigurable;
  private clubs: Club[];
  private browser: puppeteer.Browser;

  private shouldNavigateDates = () => {
    return this.htmlConfig.datesConfig != undefined;
  }

  private shouldScrapeShowDatetime = () => {
    return this.htmlConfig.showConfig?.showDateTimeSelector != undefined;
  }

  private shouldScrapeShowName = () => {
    return this.htmlConfig.showConfig?.showNameSelector != undefined;
  }

  private shouldScrapeShowTime = () => {
    return this.htmlConfig.showConfig?.showTimeSelector != undefined;
  }

  private shouldScrapeShowDate = () => {
    return this.htmlConfig.showConfig?.showDateSelector != undefined;
  }

  private shouldScrapeShowTicket = () => {
    return this.htmlConfig.showConfig?.showTicketSelector != undefined;
  }

  private dateOptionsSelector = () => {
    return this.htmlConfig.datesConfig?.dateOptionsSelector ?? "";
  }

  private dateMenuSelector = () => {
    return this.htmlConfig.datesConfig?.dateMenuSelector ?? "";
  }

  private allShowsSelector = () => {
    return this.htmlConfig.clubConfig?.allShowsSelector ?? "";
  }

  private showDateTimeSelector = () => {
    return this.htmlConfig.showConfig?.showDateTimeSelector ?? "";
  }

  private showNameSelector = () => {
    return this.htmlConfig.showConfig?.showNameSelector ?? "";
  }

  private showTimeSelector = () => {
    return this.htmlConfig.showConfig?.showTimeSelector ?? "";
  }

  private showDateSelector = () => {
    return this.htmlConfig.showConfig?.showDateSelector ?? "";
  }

  private showTicketSelector = () => {
    return this.htmlConfig.showConfig?.showTicketSelector ?? "";
  }

  private allComedianNameSelector = () => {
    return this.htmlConfig.comedianConfig?.allComedianNameSelector ?? "";
  }

  getShowDateTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return getTextValueFromSingleElement(showComponent, this.showDateTimeSelector())
  }

  getShowTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return getTextValueFromSingleElement(showComponent, this.showTimeSelector())
  }

  getShowDate = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return getTextValueFromSingleElement(showComponent, this.showDateSelector())
  }

  getShowName = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return getTextValueFromSingleElement(showComponent, this.showNameSelector())
  }

  getShowTicket = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return getHrefFromSingeElement(showComponent, this.showTicketSelector())
  }

  getAllShowElementHandlers = async (page: puppeteer.Page): Promise<puppeteer.ElementHandle<Element>[]> => {
    return getElementHandlers(page, this.allShowsSelector())
  }

  getAllDates = async (page: puppeteer.Page): Promise<string[]> => {
    return getTextValuesFromAllElements(page, this.dateOptionsSelector())
  }

  getAllComedianNames = async (showComponent: puppeteer.ElementHandle<Element>): Promise<string[]> => {
    return getTextValuesFromAllElements(showComponent, this.allComedianNameSelector())
  }

  private generatePage = () => {
    return this.browser.newPage();
  }

  constructor(jsonModel: any, browser: puppeteer.Browser) {
    this.browser = browser;
    this.baseWebsite = jsonModel[SCRAPER_KEYS.baseWebsite]
    this.htmlConfig = jsonModel[SCRAPER_KEYS.htmlConfig]
    this.textConfig = jsonModel[SCRAPER_KEYS.textConfig]
    this.clubs = jsonModel[SCRAPER_KEYS.clubs].map((config: any) => new Club(config));
  }

  public scrape = async (): Promise<Comedian[]> => {
    const tasks = this.clubs.map((club: Club) => { return this.scrapeClub(club) });

    return runTasks(tasks)
    .then((comedianArrays: Comedian[][]) => flattenComedians(comedianArrays));
  }

  scrapeClub = async (club: Club) => {

    this.logger.log(this.baseWebsite, `Started scraping ${club.name} at ${new Date()}`);

    return this.generatePage()
      .then((page: puppeteer.Page) => runTasks(this.getPageScrapingTask(page, club)))
      .then((comedianArrays: Comedian[][]) => flattenComedians(comedianArrays));
  }

  scrapePage = async (page: puppeteer.Page, club: Club): Promise<Comedian[]> => {
    this.logger.log(this.baseWebsite, `Started scraping ${club.scrapedPage}`);

    return page.goto(club.scrapedPage)
      .then(() => this.getAllShowElementHandlers(page))
      .then((showElementHandlers: puppeteer.ElementHandle<Element>[]) => this.scrapeShowElements(showElementHandlers, club));
  }

  scrapeShowElements = async (showElementHandlers: puppeteer.ElementHandle<Element>[], club: Club): Promise<Comedian[]> => {
    const showScrapingJobs = showElementHandlers.map((showElementHandler) => { return this.scrapeShow(showElementHandler, club); })
    
    return runTasks(showScrapingJobs)
    .then((comedianArrays: Comedian[][]) => flattenComedians(comedianArrays));
  }

  scrapePageTree = async (page: puppeteer.Page, club: Club) => {

    this.logger.log(this.baseWebsite, `Started scraping ${this.baseWebsite} page tree`);

    return this.getAllDates(page)
      .then((dates: string[]) => {
        const tasks = dates.map(date => { return this.selectDateAndScrapePage(date, page, club); })
        return runTasks(tasks);
      });

  }

  selectDateAndScrapePage = async (date: string, page: puppeteer.Page, club: Club) => {
    return page.select(this.dateMenuSelector(), date)
    .then(() => this.scrapePage(page, club));
  }

  scrapeShow = async (showComponent: puppeteer.ElementHandle<Element>, club: Club): Promise<Comedian[]> => {

    var jobs: Promise<string>[] = this.getShowScrapingTasks(showComponent);

    return runTasks(jobs)
    .then((scrapedValues: string[]) => buildShowFromScrapedElements(scrapedValues, club))
    .then((show: Show) => this.scrapeComedians(showComponent, show))
  }

  scrapeComedians = async (showComponent: puppeteer.ElementHandle<Element>, show: Show) => {
    return this.getAllComedianNames(showComponent)
      .then((comedianNames: string[]) => buildComedianFromScrapedElements(comedianNames, this.textConfig, show))
  }

  getPageScrapingTask = (page: puppeteer.Page, club: Club) => {
    return this.shouldNavigateDates() ? /* [this.scrapePageTree(page, club)] */ [] : [this.scrapePage(page, club)];
  }

  getShowScrapingTasks = (showComponent: puppeteer.ElementHandle<Element>) => {
 
    var jobs: Promise<string>[] = [];

    if (this.shouldScrapeShowDatetime()) {
      jobs.push(this.getShowDateTime(showComponent))
    } else {
      jobs.push(emptyStringPromise())
    }

    if (this.shouldScrapeShowTicket()) {
      jobs.push(this.getShowTicket(showComponent))
    } else {
      jobs.push(emptyStringPromise())
    }

    if (this.shouldScrapeShowDate()) {
      jobs.push(this.getShowDate(showComponent))
    } else {
      jobs.push(emptyStringPromise())
    }

    if (this.shouldScrapeShowName()) {
      jobs.push(this.getShowName(showComponent))
    } else {
      jobs.push(emptyStringPromise())
    }

    if (this.shouldScrapeShowTime()) {
      jobs.push(this.getShowTime(showComponent))
    } else {
      jobs.push(emptyStringPromise())
    }

    return jobs
  }

}