import puppeteer from "puppeteer";
import { Club } from "../classes/Club.js";
import { Comedian } from "../classes/Comedian.js";
import { PageManager } from "./PageManager.js";
import { InteractionConfig } from "../classes/InteractionConfig.js";
import { GetInteractableFunction, ScrapableElement, ScraperFunction } from "../types/scrapingFunction.js";

export class Scraper {

  private club: Club;
  private browser: puppeteer.Browser;
  private pageManager: PageManager;
  private interactionConfig: InteractionConfig;

  constructor(json: any,
    browser: puppeteer.Browser,
    pageManager: PageManager,
    interactionConfig: InteractionConfig
  ) {
    this.club = new Club(json);
    this.browser = browser;
    this.pageManager = pageManager;
    this.interactionConfig = interactionConfig;
  }

  public scrape = async (): Promise<Comedian[][]> => {
    console.log(`Started scraping ${this.club.name} at ${new Date()}`);
    return this.browser.newPage()
      .then((page: puppeteer.Page) => this.pageManager.navigateToUrl(page, this.club.schedulePageUrl))
      .then((page: puppeteer.Page) => this.pageManager.expandPage(page))
      .then((page: puppeteer.Page) => this.dispatchTasks(page))
  }

  dispatchTasks = async (page: puppeteer.Page): Promise<Comedian[][]> => {

    if (this.interactionConfig.shouldScrapeByOptionSelection) {
      return this.runScrapeLoop(page, 
        this.pageManager.optionSelectionScrape().scraperFunction,
        this.pageManager.optionSelectionScrape().firstLoopFunction
      )
    }

    else if (this.interactionConfig.shouldScrapeByDetailPage) {
      return this.runScrapeLoop(page, 
        this.pageManager.detailPageScrape().scraperFunction,
        this.pageManager.detailPageScrape().firstLoopFunction
      )
    }

    else if (this.interactionConfig.shouldScrapeByNavigationAndDetailPages) {
      return this.runScrapeLoop(page, 
        this.pageManager.navigationAndDetailPageScrape().scraperFunction,
        this.pageManager.navigationAndDetailPageScrape().firstLoopFunction,
        this.pageManager.navigationAndDetailPageScrape().secondLoopFunction
      )
    }

    return this.runScrapeLoop(page, this.pageManager.containerScrape().scraperFunction)
  }

  runScrapeLoop = async (page: puppeteer.Page, 
    scraperFunction: ScraperFunction, 
    outerloopFunction?: GetInteractableFunction, 
    innerLoopFunction?: GetInteractableFunction): Promise<Comedian[][]> => {
   
    if (outerloopFunction) {
      return outerloopFunction(page)
      .then(interactables => {
        if (innerLoopFunction) {
          return this.runScrapeLoop(page, scraperFunction, innerLoopFunction)
        }
        return this.loopAndScrape(page, interactables, scraperFunction)
      })
    }

    return this.runScraperFunction(page, scraperFunction)
  }

  runScraperFunction = async (page: puppeteer.Page,
    scraperFunction: ScraperFunction,
    input?: any
  ): Promise<Comedian[][]> => {
    if (scraperFunction.interactionFunction) {
      return scraperFunction.interactionFunction(page, input)
      .then((page: puppeteer.Page) => this.scrapeScrapeableElement(page, scraperFunction))
    }
    return this.scrapeScrapeableElement(page, scraperFunction)
  }

  scrapeScrapeableElement = async (page: puppeteer.Page, scraperFunction: ScraperFunction) => {
    return scraperFunction.getScrapableElementsFunction(page)
    .then((scrapableElement: ScrapableElement) => scraperFunction.scrapeFunction(scrapableElement))
  }

  loopAndScrape = async (page: puppeteer.Page, inputs: any, scraperFunction: ScraperFunction): Promise<Comedian[][]> => {
    var comedianArrays: Comedian[][] = [];

    for (let index = 0; index < inputs.length - 1; index++) {
      const comedians = await this.runScraperFunction(page, scraperFunction, inputs[index])
      comedianArrays = comedianArrays.concat(comedians)
    }

    return comedianArrays
  }

}