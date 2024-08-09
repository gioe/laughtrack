import puppeteer, { ElementHandle } from "puppeteer";
import Scrapable from "../types/scrapable.interface.js";
import Interactable from "../types/interactable.interface.js";
import ValidationRules from "../types/validationRules.interface.js";
import { ElementInteractor } from "./ElementInteractor.js";
import { ElementCounter } from "./ElementCounter.js";
import { ElementScaper } from "./ElementScaper.js";
import { ElementValidator } from "./ElementValidator.js";
import { InteractionConfig } from "../classes/InteractionConfig.js";
import { Comedian } from "../classes/Comedian.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";
import { ShowScraper } from "./ShowScraper.js";
import { provideGenericPromiseResponse, runTasks } from "../util/types/promiseUtil.js";
import { ClubScraper, InteractableElement } from "../types/scrapingFunction.js";

export class PageManager {

  private elementInteractor = new ElementInteractor();
  private elementCounter = new ElementCounter();
  private elementScraper = new ElementScaper();
  private elementValidator = new ElementValidator();
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

  optionSelectionScrape = (): ClubScraper => {
    return {
      firstLoopFunction: this.getAllOptions,
      scraperFunction: {
        interactionFunction: this.selectOption,
        getScrapableElementsFunction: this.getContainers,
        scrapeFunction: this.scrapeContainers
      }
    }
  }

  detailPageScrape = (): ClubScraper => {
    return {
      firstLoopFunction: this.getDetailPageLinks,
      scraperFunction: {
        interactionFunction: this.clickValidLink,
        getScrapableElementsFunction: this.getContainers,
        scrapeFunction: this.scrapeContainers
      }
    }
  }

  navigationAndDetailPageScrape = (): ClubScraper => {
    return {
      firstLoopFunction: this.getLoopCount,
      secondLoopFunction: this.getDetailPageLinks,
      scraperFunction: {
        interactionFunction: this.clickValidLink,
        getScrapableElementsFunction: this.getContainers,
        scrapeFunction: this.scrapeContainers
      }
    }
  }

  containerScrape = (): ClubScraper => {
    return {
      scraperFunction: {
        getScrapableElementsFunction: this.getContainers,
        scrapeFunction: this.scrapeContainers
      }
    }
  }

  getValidationRules = (): ValidationRules => {
    return {
      requiredSelectors: this.scrapingConfig.requiredSelectors,
      invalidText: this.scrapingConfig.invalidLinkText
    }
  }

  getAllOptions = async (scrapable: Scrapable): Promise<string[]> => {
    console.log("GETTING ALL OPTIONS")
    return this.elementScraper.getAllValues(scrapable, this.scrapingConfig.optionsSelector)
  }

  selectOption = async (interactable: InteractableElement, input?: any): Promise<puppeteer.Page> => {
    console.log(`SELECTING ${input}`)

    return this.elementInteractor.select(interactable, this.interactionConfig.selectSelector, input)
  }

  getContainers = async (scrapable: Scrapable): Promise<ElementHandle<Element>[]> => {
    console.log(`GETTING CONTAINERS USING ${this.scrapingConfig.showDetailContainerSelector}`)
    return this.elementScraper.getAllElementsHandlers(scrapable, this.scrapingConfig.showDetailContainerSelector)
  }

  scrapeContainers = async (scrapable: any): Promise<Comedian[][]> => {

    console.log(`SCRAPING ${scrapable.length} CONTAINERS`)

    const tasks = (scrapable as Scrapable[]).map(s => this.showScraper.scrapeShowDetailContainer(s))
    return runTasks(tasks)
  }

  getDetailPageLinks = async (scrapable: Scrapable): Promise<ElementHandle<Element>[]> => {
    console.log(`GETTING LINKS USING ${this.scrapingConfig.showDetailContainerSelector}`)
    return this.elementScraper.getAllElementsHandlers(scrapable, this.scrapingConfig.showDetailContainerSelector)
  }

  clickValidLink = async (interactable: InteractableElement, input?: any): Promise<puppeteer.Page> => {
    return this.elementValidator.validateElement(input, this.getValidationRules())
      .then(valid => valid ? this.elementInteractor.click(interactable, "") : interactable as puppeteer.Page )
  }

  scrapeDetailPage = async (page: puppeteer.Page): Promise<Comedian[][]> => {
    return this.showScraper.scrapeShowDetailPage(page)
  }

  getLoopCount = (scrapable: Scrapable) => {
    return provideGenericPromiseResponse([1, 2, 3])
  }

  navigatePagesAndScrape = async (page: puppeteer.Page): Promise<Comedian[][]> => {
    return this.getDetailPageLinks(page).then(links => {
      return [];
    })
  }

  navigateToUrl = async (page: puppeteer.Page, url: string): Promise<puppeteer.Page> => {
    return page.goto(url)
      .then(() => page)
  }

  expandPage = async (page: puppeteer.Page): Promise<puppeteer.Page> => {
    return this.elementCounter.getElementCount(page, this.interactionConfig.moreShowsButtonSelector)
      .then((count: number) => {
        if (count == 0) {
          throw new Error(`No elements found`);
        }
        return this.elementInteractor.click(page, this.interactionConfig.moreShowsButtonSelector)
      })
      .then((page: puppeteer.Page) => this.expandPage(page))
      .catch(() => page)
  }

  getNextPageLink = (page: puppeteer.Page): Promise<string> => {
    return this.elementScraper.getHref(page, this.interactionConfig.nextPageLinkSelector);
  }


}