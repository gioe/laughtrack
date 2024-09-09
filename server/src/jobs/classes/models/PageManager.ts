import playwright, { ElementHandle } from "playwright";
import { ElementInteractor } from "../handlers/ElementInteractor.js";
import { ElementValidator } from "../handlers/ElementValidator.js";
import { ShowScraper } from "../scrapers/ShowScraper.js";
import { runTasks } from "../../../common/util/promiseUtil.js";
import { ElementHandler } from "../handlers/ElementHandler.js";
import { Scrapable } from "../../../common/interfaces/scrapable.interface.js";
import { ShowInterface } from "../../../common/interfaces/show.interface.js";
import { ScrapableScraper } from "../scrapers/ScrapableScraper.js";
import { ScrapingConfig } from "./ScrapingConfig.js";
import { generateCompleteUrl } from "../../util/scrapableUtil.js";

export class PageManager {

  private elementInteractor = new ElementInteractor();
  private scraper = new ScrapableScraper();
  private elementValidator = new ElementValidator();
  private elementHandler = new ElementHandler();
  private scrapingConfig: ScrapingConfig;
  private showScraper: ShowScraper;

  constructor(
    config: any,
  ) {
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

  scrapeContainers = async (scrapable: Scrapable, input?: any): Promise<ShowInterface[]> => {
    
    return this.getShowContainers(scrapable as playwright.Page)
      .then((elementHandlers: ElementHandle<Element>[]) => {
        const tasks = elementHandlers.map(handler => this.showScraper.scapeShow(handler, input))
        return runTasks(tasks)
      })
  }

  scrapeDetailPage = async (scrapable: Scrapable): Promise<ShowInterface[]> => {
    const page = scrapable as playwright.Page
    return this.showScraper.scapeShow(page, page.url()).then((show: ShowInterface) => [show])
  }

  navigateToUrl = async (page: playwright.Page, input?: string): Promise<playwright.Page> => {
    if (input) return page.goto(input).then(() => page)
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