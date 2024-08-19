import playwright, { ElementHandle } from "playwright";
import { ElementInteractor } from "./ElementInteractor.js";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { ElementValidator } from "./ElementValidator.js";
import { InteractionConfig } from "../classes/InteractionConfig.js";
import { Comedian } from "../classes/Comedian.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";
import { ShowScraper } from "./ShowScraper.js";
import { runTasks } from "../util/types/promiseUtil.js";
import { ElementHandler } from "./ElementHandler.js";
import { Scrapable } from "../types/scrapable.interface.js";
import { generateCompleteUrl } from "../util/types/scrapableUtil.js";

export class PageManager {

  private elementInteractor = new ElementInteractor();
  private scraper = new ScrapableScraper();
  private elementValidator = new ElementValidator();
  private elementHandler = new ElementHandler();

  private interactionConfig: InteractionConfig;
  private scrapingConfig: ScrapingConfig;
  private showScraper: ShowScraper;

  constructor(interactionConfig: InteractionConfig,
    scrapingConfig: ScrapingConfig,
  ) {
    this.interactionConfig = interactionConfig;
    this.scrapingConfig = scrapingConfig;
    this.showScraper = new ShowScraper(scrapingConfig)
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

  scrapeContainers = async (scrapable: Scrapable, input?: any): Promise<Comedian[][]> => {
    return this.getShowContainers(scrapable as playwright.Page)
      .then((elementHandlers: ElementHandle<Element>[]) => {
        const tasks = elementHandlers.map(handler => this.showScraper.scapeShow(handler, input))
        return runTasks(tasks)
      })
  }

  scrapeDetailPage = async (scrapable: Scrapable): Promise<Comedian[][]> => {
    const page = scrapable as playwright.Page
    return this.showScraper.scapeShow(page, page.url()).then((comedianArray: Comedian[]) => [comedianArray])
  }

  navigateToUrl = async (page: playwright.Page, input?: string): Promise<playwright.Page> => {
    console.log(`Navigating to ${input}`)
    if (input) return page.goto(input).then(() => page)
    return page
  }

  expandPage = async (page: playwright.Page): Promise<playwright.Page> => {
    return this.elementInteractor.clickPageButton(page, this.interactionConfig.moreShowsButtonSelector)
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