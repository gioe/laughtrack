import puppeteer from "puppeteer";
import { providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { ElementScaper } from "./ElementScaper.js";
import { createShow } from "../util/types/showUtil.js";
import { DateTimeScraper } from "./DateTimeScraper.js";
import { Club } from "../classes/Club.js";
import { ProvidedScrapingValue } from "../types/providedScrapingValue.interface.js";
import { Comedian } from "../classes/Comedian.js";
import { ComedianScraper } from "./ComedianScraper.js";
import Scrapable from "../types/scrapable.interface.js";

export class ShowScraper {

  club: Club;
  dateTimeScraper: DateTimeScraper;
  comedianScraper: ComedianScraper;
  elementScraper = new ElementScaper();

  constructor(
    club: Club,
    comedianScraper: ComedianScraper,
    dateTimeScraper: DateTimeScraper
  ) {
    this.club = club;
    this.comedianScraper = comedianScraper
    this.dateTimeScraper = dateTimeScraper;
  }

  getShowTicketJob = async (showComponent: Scrapable, url?: string) => {
    return url ? providedStringPromise(url) : this.getShowTicket(showComponent)
  }

  getShowTicket = async (showComponent: Scrapable) => {
    return this.elementScraper.getElementCount(showComponent, this.club.showConfig.ticketLinkSelector)
      .then((count: number) => count > 0 ? this.elementScraper.getHrefFrom(showComponent, this.club.showConfig.ticketLinkSelector) : "")
  }

  getShowScrapingTasks = (showComponent: Scrapable, 
    providedScrapingValues?: ProvidedScrapingValue) => {
    const datetimeJob = this.dateTimeScraper.getShowDateTimeJob(showComponent, providedScrapingValues?.date)
    const ticketJob = this.getShowTicketJob(showComponent, providedScrapingValues?.ticketUrl)
    return [datetimeJob, ticketJob]
  }

  scrapeSchedulePage = async (showElementHandlers: puppeteer.ElementHandle<Element>[],
    providedScrapingValues?: ProvidedScrapingValue
  ): Promise<Comedian[][]> => {

    console.log(`Scraping ${showElementHandlers.length} shows`)
    
    const showScrapingJobs = showElementHandlers
      .map((showElementHandler: puppeteer.ElementHandle<Element>) => this.scrapeShow(showElementHandler, providedScrapingValues))

    return runTasks(showScrapingJobs)
  }

  scrapeDetailPage = async (page: puppeteer.Page,
    providedScrapingValues?: ProvidedScrapingValue
  ): Promise<Comedian[]> => {

    return this.comedianScraper.getAllComedians(page)
      .then((comedians: Comedian[]) => this.runShowScrapingTasks(page, comedians, providedScrapingValues))
  }

  scrapeShow = async (showElementHandler: puppeteer.ElementHandle<Element>,
    providedScrapingValues?: ProvidedScrapingValue): Promise<Comedian[]> => {

    return this.comedianScraper.getAllComedians(showElementHandler)
      .then((comedians: Comedian[]) => this.runShowScrapingTasks(showElementHandler, comedians, providedScrapingValues))

  }

  runShowScrapingTasks = async (showComponent: Scrapable,
    comedians: Comedian[],
    providedScrapingValue?: ProvidedScrapingValue
  ): Promise<Comedian[]> => {

    var jobs: Promise<string>[] = this.getShowScrapingTasks(showComponent, providedScrapingValue);

    return runTasks(jobs)
      .then((scrapedValues: string[]) => this.addShowToComedians(scrapedValues, comedians));
  }

  addShowToComedians = (scrapedValues: string[], comedians: Comedian[]) => {

    const show = createShow(
      {
        dateTimeString: scrapedValues[0],
        ticketString: scrapedValues[1]
      },
      this.club,
    )

    comedians.forEach((comedian: Comedian) => {
      comedian.addShow(show)
    })

    return comedians;
  }

}