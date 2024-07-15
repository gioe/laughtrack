import puppeteer from "puppeteer";
import { Logger } from "./Logger.js";
import { Club } from './Club.js';
import { emptyStringPromise, providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { ElementScaper } from "./ElementScaper.js";
import { Comedian } from "./Comedian.js";
import { createShow } from "../util/types/showUtil.js";
import { ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";


export class ShowScraper {
  club: Club;
  json: any;
  elementScraper: ElementScaper;
  logger: Logger;

  constructor(
    club: Club,
    json: any,
    elementScraper: ElementScaper,
    logger: Logger,
  ) {
    this.club = club;
    this.json = json;
    this.elementScraper = elementScraper
    this.logger = logger;
  }

  private getShowHtmlConfig = (): ShowHTMLConfiguration => {
    return this.json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.showConfig];
  }

  private shouldScrapeShowDatetime = () => {
    return this.getShowHtmlConfig().showDateTimeSelector != undefined;
  }

  private shouldScrapeShowName = () => {
    return this.getShowHtmlConfig().showNameSelector != undefined;
  }

  private shouldScrapeShowTime = () => {
    return this.getShowHtmlConfig().showTimeSelector != undefined;
  }

  private shouldScrapeShowDate = () => {
    return this.getShowHtmlConfig().showDateSelector != undefined;
  }

  private shouldScrapeShowTicket = () => {
    return this.getShowHtmlConfig().showTicketSelector != undefined;
  }

  private showDateTimeSelector = () => {
    return this.getShowHtmlConfig().showDateTimeSelector ?? "";
  }

  private showTimeSelector = () => {
    return this.getShowHtmlConfig().showTimeSelector ?? "";
  }

  private showDateSelector = () => {
    return this.getShowHtmlConfig().showDateSelector ?? "";
  }

  private showNameSelector = () => {
    return this.getShowHtmlConfig().showNameSelector ?? "";
  }

  private showTicketSelector = () => {
    return this.getShowHtmlConfig().showTicketSelector ?? "";
  }

  getShowDateTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextValueFromSingleElement(showComponent, this.showDateTimeSelector())
  }

  getShowTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextValueFromSingleElement(showComponent, this.showTimeSelector())
  }

  getShowDate = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextValueFromSingleElement(showComponent, this.showDateSelector())
  }

  getShowName = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextValueFromSingleElement(showComponent, this.showNameSelector())
  }

  getShowTicket = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getHrefFromSingeElement(showComponent, this.showTicketSelector())
  }

  getShowScrapingTasks = (showComponent: puppeteer.ElementHandle<Element>, date?: string) => {
    var jobs: Promise<string>[] = [];

    if (this.shouldScrapeShowDatetime()) {
      jobs.push(this.getShowDateTime(showComponent))
    } else {
      jobs.push(emptyStringPromise())
    }

    if (this.shouldScrapeShowDate()) {
      jobs.push(this.getShowDate(showComponent))
    } else if (date) {
      jobs.push(providedStringPromise(date))
    } else {
      jobs.push(emptyStringPromise())
    }

    if (this.shouldScrapeShowTime()) {
      jobs.push(this.getShowTime(showComponent))
    } else {
      jobs.push(emptyStringPromise())
    }

    if (this.shouldScrapeShowName()) {
      jobs.push(this.getShowName(showComponent))
    } else {
      jobs.push(emptyStringPromise())
    }

    if (this.shouldScrapeShowTicket()) {
      jobs.push(this.getShowTicket(showComponent))
    } else {
      jobs.push(emptyStringPromise())
    }

    return jobs
  }

  scrapeShowForComedians = async (showComponent: puppeteer.ElementHandle<Element>,
    comedians: Comedian[],
    club: Club,
    date?: string): Promise<Comedian[]> => {

    var jobs: Promise<string>[] = this.getShowScrapingTasks(showComponent, date);

    return runTasks(jobs)
      .then((scrapedValues: string[]) => this.buildShowFromScrapedElements(scrapedValues, comedians, club, date));
  }

  buildShowFromScrapedElements = (scrapedValues: string[],
    comedians: Comedian[],
    club: Club,
    date?: string): Comedian[] => {

      this.log(scrapedValues)
    const show = createShow(scrapedValues, club, this.getShowHtmlConfig(), date)

    comedians.forEach((comedian: Comedian) => {
      comedian.addShow(show)
      return comedian
    })

    return comedians;
  }


  // #region Logger
  log = (input: any) => {
    this.logger.log(this.club.getScrapedPage(), input)
  }
  // #endregion

}