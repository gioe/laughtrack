import playwright, { ElementHandle } from "playwright";
import { ElementInteractor } from "./ElementInteractor.js";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { ElementValidator } from "./ElementValidator.js";
import { InteractionConfig } from "../classes/InteractionConfig.js";
import { Comedian } from "../classes/Comedian.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";
import { ShowScraper } from "./ShowScraper.js";
import { provideGenericPromiseResponse, runTasks } from "../util/types/promiseUtil.js";
import { ScrapableElement } from "../types/scrapingFunction.js";
import { ElementHandler } from "./ElementHandler.js";
import { Scrapable } from "../types/scrapable.interface.js";

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
      .then((elementHandlers: ElementHandle<Element>[]) => {
        return this.elementHandler.getAllHrefs(scrapable, elementHandlers)
      })
  }

  getLoopCount = (): Promise<number[]> => {
    const pagesToScrape = this.scrapingConfig.pagesToScrape ?? 0
    var values: number[] = []

    for (let index = 0; index < pagesToScrape - 1; index++) {
      values.push(index)
    }

    return provideGenericPromiseResponse(values)
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

  navigateToUrl = async (page: playwright.Page, input?: any): Promise<playwright.Page> => {
    console.log(`Navigating to ${input}`)
    if (input) return page.goto(input as string).then(() => page)
    return page
  }

  expandPage = async (page: playwright.Page): Promise<playwright.Page> => {
    console.log(`Checking if we can expand ${page.url()}`)

    return this.elementInteractor.clickPageButton(page, this.interactionConfig.moreShowsButtonSelector)
      .then((page: playwright.Page) => this.expandPage(page))
      .catch(() => page)
  }

  getNextPageLink = (page: playwright.Page): Promise<string> => {
    return this.scraper.getHref(page, this.interactionConfig.nextPageLinkSelector);
  }

}