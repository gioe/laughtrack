import playwright, { ElementHandle } from "playwright-core";import { ElementInteractor } from "../../jobs/scrape/elementHandlers/ElementInteractor.js";
import { ScrapableScraper } from "../../jobs/scrape/scrapers/ScrapableScraper.js";
import { ElementValidator } from "../../jobs/scrape/elementHandlers/ElementValidator.js";
import { ElementHandler } from "../../jobs/scrape/elementHandlers/ElementHandler.js";
import { ScrapingConfig } from "./ScrapingConfig.js";
import { ShowScraper } from "../../jobs/scrape/scrapers/ShowScraper.js";
import { Scrapable } from "./interfaces/scrape.interface.js";
import { generateCompleteUrl } from "../util/scrapableUtil.js";
import { Show } from "./Show.js";
import { runTasks } from "../util/promiseUtil.js";;

export class PageManager {

  private elementInteractor = new ElementInteractor();
  private scraper = new ScrapableScraper();
  private elementValidator = new ElementValidator();
  private elementHandler = new ElementHandler();
  private scrapingConfig: ScrapingConfig;
  private showScraper: ShowScraper;

  constructor(config: any,) {
    this.scrapingConfig = new ScrapingConfig(config)
    this.showScraper = new ShowScraper(this.scrapingConfig)
  }

  getAllDateOptions = async (scrapable: Scrapable): Promise<string[]> => {
    return this.scraper.getAllValues(scrapable, this.scrapingConfig.dateOptionsSelector)
  }

  getShowContainers = async (scrapable: Scrapable): Promise<ElementHandle<Element>[]> => {
    return this.scraper.getAllElementsHandlers(scrapable, this.scrapingConfig.showDetailContainerSelector)
  }

  getValidDetailPageLinks = async (scrapable: Scrapable): Promise<string[]> => {
    return this.scraper.getAllElementsHandlers(scrapable, this.scrapingConfig.detailPageButtonSelector)
      .then((buttons: ElementHandle<Element>[]) => {
        return this.elementValidator.filterInvalidElements(buttons,
          {
            invalidText: this.scrapingConfig.invalidLinkText
          })
      })
      .then((elementHandlers: ElementHandle<Element>[]) => this.elementHandler.getAllHrefs(scrapable, elementHandlers))
  }

  getAllPageLinks = async (scrapable: Scrapable, allPageLinks?: string[]): Promise<string[]> => {
    const page = scrapable as playwright.Page;
    var pageLinks = allPageLinks ?? []

    return this.getNextPageLink(page)
    .then((link: string) => {
      const completeUrl = generateCompleteUrl(page, link);
      if (!pageLinks.includes(completeUrl)) {
        pageLinks.push(completeUrl)
        return this.navigateToUrl(page, completeUrl)
      }
      throw new Error("Page is already in the link list. Breaking loop")
    })
    .then((page: playwright.Page) => this.getAllPageLinks(page, pageLinks))
    .catch((error) => {
      console.warn(error)
      return pageLinks
    })
  }

  selectDateOption = async (page: playwright.Page, option?: string): Promise<playwright.Page> => {
    return this.elementInteractor.select(page, this.scrapingConfig.dateSelectSelector, option)
  }

  scrapeContainers = async (scrapable: Scrapable, input?: any): Promise<Show[]> => {
    return this.getShowContainers(scrapable as playwright.Page)
      .then((elementHandlers: ElementHandle<Element>[]) => {
        const tasks = elementHandlers.map(handler => this.showScraper.scapeShow(handler, input))
        return runTasks(tasks)
      })
  }

  scrapeDetailPage = async (scrapable: Scrapable): Promise<Show[]> => {
    const page = scrapable as playwright.Page
    return this.showScraper.scapeShow(page, page.url()).then((show: Show) => [show])
  }

  navigateToUrl = async (page: playwright.Page, input?: string): Promise<playwright.Page> => {
    if (input) return page.goto(input, { timeout: 50000, waitUntil: "domcontentloaded" },
    ).then(() => page)
    return page
  }

  expandPage = async (page: playwright.Page): Promise<playwright.Page> => {
    return this.elementInteractor.clickPageButton(page, this.scrapingConfig.moreShowsButtonSelector)
      .then((page: playwright.Page) => this.expandPage(page))
      .catch((error) => {
        console.warn(error)
        return page
      })
  }

  getNextPageLink = (page: playwright.Page): Promise<string> => {
    return this.scraper.getHref(page, this.scrapingConfig.nextPageLinkSelector);
  }

}