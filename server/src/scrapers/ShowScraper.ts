import puppeteer from "puppeteer";
import { providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { ElementScaper } from "./ElementScaper.js";
import { createShow } from "../util/types/showUtil.js";
import { ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { Show } from "../types/show.interface.js";
import { DateTimeScraper } from "./DateTimeScraper.js";
import { Club } from "../classes/Club.js";

export class ShowScraper {
  club: Club;
  json: any;
  dateTimeScraper: DateTimeScraper;
  elementScraper = new ElementScaper();

  constructor(
    club: Club,
    json: any,
    dateTimeScraper: DateTimeScraper
  ) {
    this.club = club;
    this.json = json;
    this.dateTimeScraper = dateTimeScraper;
  }

  private getShowHtmlConfig = (): ShowHTMLConfiguration => {
    return this.json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.showConfig];
  }

  private shouldScrapeShowName = () => {
    return this.getShowHtmlConfig().showNameSelector != undefined;
  }

  private showNameSelector = () => {
    return this.getShowHtmlConfig().showNameSelector ?? "";
  }

  private showTicketSelector = () => {
    return this.getShowHtmlConfig().showTicketSelector ?? "";
  }

  getShowNameJob = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.shouldScrapeShowName() ? this.getShowName(showComponent) : providedStringPromise("")
  }

  getShowTicketJob = async (showComponent: puppeteer.ElementHandle<Element>, url?: string) => {
    return url ? providedStringPromise(url) : this.getShowTicket(showComponent)
  }

  getShowName = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getTextValueFromSingleElement(showComponent, this.showNameSelector())
  }

  getShowTicket = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getElementCount(showComponent, this.showTicketSelector())
    .then((count: number) => count > 0 ? this.elementScraper.getHrefFromSingleElement(showComponent, this.showTicketSelector()) : "")
  }

  getShowScrapingTasks = (showComponent: puppeteer.ElementHandle<Element>, date?: string, url?: string) => {
    const datetimeJob = this.dateTimeScraper.getShowDateTimeJob(showComponent, date)
    const showNameJob = this.getShowNameJob(showComponent)
    const ticketJob = this.getShowTicketJob(showComponent, url)
    return [datetimeJob, showNameJob, ticketJob]
  }

  scrapeShow = async (showComponent: puppeteer.ElementHandle<Element>,
    date?: string,
    url?: string): Promise<Show> => {

    var jobs: Promise<string>[] = this.getShowScrapingTasks(showComponent, date, url);

    return runTasks(jobs)
      .then((scrapedValues: string[]) => {
        return createShow(
          { 
            dateTimeString: scrapedValues[0], 
            nameString: scrapedValues[1], 
            ticketString: scrapedValues[2]
          }, 
          this.club, 
          this.getShowHtmlConfig()
        )
    });
  }

}