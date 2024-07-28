import puppeteer from "puppeteer";
import { providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { ElementScaper } from "./ElementScaper.js";
import { createShow } from "../util/types/showUtil.js";
import { ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { Show } from "../types/show.interface.js";
import { DateTimeScraper } from "./DateTimeScraper.js";
import { Club } from "../classes/Club.js";
import { ProvidedScrapingValue } from "../types/providedScrapingValue.interface.js";

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
  private showTicketSelector = () => {
    return this.getShowHtmlConfig().showTicketSelector ?? "";
  }

  getShowTicketJob = async (showComponent: puppeteer.ElementHandle<Element>, url?: string) => {
    return url ? providedStringPromise(url) : this.getShowTicket(showComponent)
  }

  getShowTicket = async (showComponent: puppeteer.ElementHandle<Element>) => {
    return this.elementScraper.getElementCount(showComponent, this.showTicketSelector())
    .then((count: number) => count > 0 ? this.elementScraper.getHrefFromSingleElement(showComponent, this.showTicketSelector()) : "")
  }

  getShowScrapingTasks = (showComponent: puppeteer.ElementHandle<Element>, providedScrapingValues?: ProvidedScrapingValue) => {
    const datetimeJob = this.dateTimeScraper.getShowDateTimeJob(showComponent, providedScrapingValues?.date)
    const ticketJob = this.getShowTicketJob(showComponent, providedScrapingValues?.ticketUrl)
    return [datetimeJob, ticketJob]
  }

  scrapeShow = async (showComponent: puppeteer.ElementHandle<Element>,
    providedScrapingValues?: ProvidedScrapingValue): Promise<Show> => {

    var jobs: Promise<string>[] = this.getShowScrapingTasks(showComponent, providedScrapingValues);

    return runTasks(jobs)
      .then((scrapedValues: string[]) => {
        return createShow(
          { 
            dateTimeString: scrapedValues[0], 
            ticketString: scrapedValues[1]
          }, 
          this.club, 
          this.getShowHtmlConfig()
        )
    });
  }

}