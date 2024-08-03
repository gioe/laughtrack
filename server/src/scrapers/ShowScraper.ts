import puppeteer from "puppeteer";
import { runTasks } from "../util/types/promiseUtil.js";
import { ElementScaper } from "./ElementScaper.js";
import { createShow } from "../util/types/showUtil.js";
import { DateTimeScraper } from "./DateTimeScraper.js";
import { Club } from "../classes/Club.js";
import { ProvidedScrapingValue } from "../types/providedScrapingValue.interface.js";
import { Comedian } from "../classes/Comedian.js";
import { ComedianScraper } from "./ComedianScraper.js";
import Scrapable from "../types/scrapable.interface.js";
import { TicketScraper } from "./TicketScraper.js";
import { DateTimeContainer } from "../classes/DateTimeContainer.js";

export class ShowScraper {

  private club: Club;
  private comedianScraper: ComedianScraper;
  private dateTimeScraper: DateTimeScraper;
  private ticketScraper: TicketScraper;
  private elementScraper = new ElementScaper();

  constructor(club: Club) {
    this.club = club;
    this.dateTimeScraper = new DateTimeScraper(club);
    this.ticketScraper = new TicketScraper(club);
    this.comedianScraper = new ComedianScraper(club);
  }

  getAllShowsOnPage = async (page: puppeteer.Page): Promise<puppeteer.ElementHandle<Element>[]> => {
    return this.elementScraper.getAllElementsHandlersFrom(page, this.club.clubConfig.showSelector)
  }

  runShowScrapingTasks = async (showComponent: Scrapable,
    comedians: Comedian[],
    providedScrapingValues?: ProvidedScrapingValue): Promise<Comedian[]> => {
    
    if (comedians.length == 0) return []
    
    this.writeLog(providedScrapingValues)

    const datetimeTask = this.dateTimeScraper.getShowDateTimeTask(showComponent, providedScrapingValues?.date)
    const ticketTask = this.ticketScraper.getShowTicketTask(showComponent, providedScrapingValues?.ticketUrl)
    
    return runTasks([datetimeTask, ticketTask])
    .then((scrapedValues: any[]) => this.addShowToComedians(scrapedValues, comedians))

  }

  scrapeAllShows = async (page: puppeteer.Page,
    providedScrapingValues?: ProvidedScrapingValue
  ): Promise<Comedian[][]> => {

    return this.getAllShowsOnPage(page)
      .then((showElements: puppeteer.ElementHandle<Element>[]) => {
      
        if (showElements.length == 0) return []

        console.log(`Scraping ${showElements.length} shows`)

        const showScrapingJobs = showElements
        .map((showElementHandler: puppeteer.ElementHandle<Element>) => this.scrapeShow(showElementHandler, providedScrapingValues))
        
        return runTasks(showScrapingJobs)
      })
  }

  scrapeShow = async (showElementHandler: Scrapable,
    providedScrapingValues?: ProvidedScrapingValue): Promise<Comedian[]> => {

    return this.comedianScraper.getAllComedians(showElementHandler)
      .then((comedians: Comedian[]) => this.runShowScrapingTasks(showElementHandler, comedians, providedScrapingValues))
   
    }

  addShowToComedians = (scrapedValues: string[], comedians: Comedian[]) => {

    const show = createShow(
      {
        dateTimeContainer: new DateTimeContainer(scrapedValues[0], this.club.showConfig),
        ticketString: scrapedValues[1]
      },
      this.club,
    )

    comedians.forEach((comedian: Comedian) => {
      comedian.addShow(show)
    })

    return comedians;
  }
  
  writeLog = (providedScrapingValues?: ProvidedScrapingValue) => {
    
    if (providedScrapingValues?.ticketUrl) {
      console.log(`Scraping ${providedScrapingValues?.ticketUrl}`)
    }

  }
}