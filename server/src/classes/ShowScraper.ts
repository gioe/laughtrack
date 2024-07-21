import puppeteer from "puppeteer";
import { Logger } from "./Logger.js";
import { Club } from './Club.js';
import { emptyStringPromise, providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { ElementScaper } from "./ElementScaper.js";
import { Comedian } from "./Comedian.js";
import { combinedScrapedDatesAndTime, createShow, normalizeDatetime } from "../util/types/showUtil.js";
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
    .then((datetime: string) => {
      return normalizeDatetime(datetime)
    })
  }
  
  getShowDateTimeJob = async (showComponent: puppeteer.ElementHandle<Element>, date?: string) => {
    return this.shouldScrapeShowDatetime() ? this.getShowDateTime(showComponent) : this.combineDateAndTime(showComponent, date)
  }

  combineDateAndTime = async (showComponent: puppeteer.ElementHandle<Element>, date?: string) => {
    const dateTask = date ? providedStringPromise(date) : this.getShowDate(showComponent)
    const timeTask = this.getShowTime(showComponent)
    
    return runTasks([dateTask, timeTask])
    .then((scrapedValues: string[]) => combinedScrapedDatesAndTime(scrapedValues, this.getShowHtmlConfig()))
  }

  getShowNameJob = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.shouldScrapeShowName() ? this.getShowName(showComponent) : providedStringPromise("")
  }

  getShowTicketJob = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.shouldScrapeShowName() ? this.getShowTicket(showComponent) : providedStringPromise("")
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
    const datetimeJob = this.getShowDateTimeJob(showComponent, date)
    const showNameJob = this.getShowNameJob(showComponent)
    const ticketJob = this.getShowTicketJob(showComponent)
    return [datetimeJob, showNameJob, ticketJob]
  }

  scrapeShowForComedians = async (showComponent: puppeteer.ElementHandle<Element>,
    comedians: Comedian[],
    date?: string): Promise<Comedian[]> => {

    var jobs: Promise<string>[] = this.getShowScrapingTasks(showComponent, date);

    return runTasks(jobs)
      .then((scrapedValues: string[]) => this.buildShowFromScrapedElements(scrapedValues, comedians, date));
  }

  buildShowFromScrapedElements = (scrapedValues: string[],
    comedians: Comedian[],
    date?: string): Comedian[] => {

    const show = createShow(scrapedValues, this.club, this.getShowHtmlConfig())
    
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