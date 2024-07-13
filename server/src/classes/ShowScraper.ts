import puppeteer from "puppeteer";
import { Logger } from "./Logger.js";
import { Show } from '../types/show.interface.js';
import { Club } from './Club.js';
import { buildDateFromDateTimeString } from '../util/types/dateTime.js';
import { emptyStringPromise, providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { Scraper } from "./Scraper.js";
import { Comedian } from "./Comedian.js";

export class ShowScraper {
  logger: Logger;
  showConfig: ShowHTMLConfiguration;
  scraper: Scraper;

  constructor(logger: Logger,
    json: any) {
    this.logger = logger;
    this.showConfig = json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.showConfig];
    this.scraper = new Scraper(logger, json[SCRAPER_KEYS.scrapedPage])
  }

  private shouldScrapeShowDatetime = () => {
    return this.showConfig.showDateTimeSelector != undefined;
  }

  private shouldScrapeShowName = () => {
    return this.showConfig.showNameSelector != undefined;
  }

  private shouldScrapeShowTime = () => {
    return this.showConfig.showTimeSelector != undefined;
  }

  private shouldScrapeShowDate = () => {
    return this.showConfig.showDateSelector != undefined;
  }

  private shouldScrapeShowTicket = () => {
    return this.showConfig.showTicketSelector != undefined;
  }

  private showDateTimeSelector = () => {
    return this.showConfig.showDateSelector ?? "";
  }

  private showTimeSelector = () => {
    return this.showConfig.showTimeSelector ?? "";
  }

  private showDateSelector = () => {
    return this.showConfig.showDateSelector ?? "";
  }

  private showNameSelector = () => {
    return this.showConfig.showNameSelector ?? "";
  }

  private showTicketSelector = () => {
    return this.showConfig.showTicketSelector ?? "";
  }

  getShowDateTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.scraper.getTextValueFromSingleElement(showComponent, this.showDateTimeSelector())
  }

  getShowTime = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.scraper.getTextValueFromSingleElement(showComponent, this.showTimeSelector())
  }

  getShowDate = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.scraper.getTextValueFromSingleElement(showComponent, this.showDateSelector())
  }

  getShowName = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.scraper.getTextValueFromSingleElement(showComponent, this.showNameSelector())
  }

  getShowTicket = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.scraper.getHrefFromSingeElement(showComponent, this.showTicketSelector())
  }

  getShowScrapingTasks = (showComponent: puppeteer.ElementHandle<Element>, date?: string) => {
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
    } else if (date) {
      jobs.push(providedStringPromise(date))
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

  scrapeShowForComedians = async (showComponent: puppeteer.ElementHandle<Element>,
    comedians: Comedian[],
    club: Club,
    date?: string): Promise<Comedian[]> => {

    var jobs: Promise<string>[] = this.getShowScrapingTasks(showComponent, date);

    return runTasks(jobs)
      .then((scrapedValues: string[]) => this.buildShowFromScrapedElements(scrapedValues, comedians, club, date))
  }

  buildShowFromScrapedElements = (scrapedValues: string[], comedians: Comedian[], club: Club, date?: string): Comedian[] => {
    const formattedDateTime = this.formatShowDateTimes(scrapedValues[0], scrapedValues[1], scrapedValues[2]);
    const formattedName = this.formatShowName(scrapedValues[3]);
    const formattedTicketLink = this.formatShowTicketLink(scrapedValues[4]);

    const show =  {
      clubName: club.name,
      clubWebsite: club.scrapedPage,
      dateTime: formattedDateTime,
      name: formattedName,
      ticketLink: formattedTicketLink,
    } as Show

    comedians.forEach((comedian: Comedian) => {
      comedian.addShow(show)
      return comedian
    })
    return comedians;
  }

  formatShowDateTimes = (dateTime: string, date: string, time: string): Date => {

    if (dateTime) {
      return buildDateFromDateTimeString(dateTime)
    }
    //TODO: Handle cases where the date and time are separate strings
    return new Date()
  }

  formatShowName = (name: string): string => {
    return "";
  }

  formatShowTicketLink = (ticketLink: string): string => {
    return ticketLink
  }

  // #region Logger
  log = (input: any) => {
    this.logger.log(this.scraper.scrapedPage, input)
  }
  // #endregion

}