import playwright from "playwright-core";
import { ElementInteractor } from "../elementHandlers/ElementInteractor.js";
import { ScrapableScraper } from "./ScrapableScraper.js";
import { ShowScraper } from "./ShowScraper.js";
import { providedPromiseResponse } from "../../../common/util/promiseUtil.js";
import { Show } from "../../../common/models/classes/Show.js";
import { ScrapingConfig } from "./ScrapingConfig.js";

export class PageManager {

  private elementInteractor = new ElementInteractor();
  private scraper = new ScrapableScraper();
  private scrapingConfig: ScrapingConfig;
  private showScraper: ShowScraper;

  constructor(config: any,) {
    this.scrapingConfig = new ScrapingConfig(config)
    this.showScraper = new ShowScraper(this.scrapingConfig)
  }

  getAllDateOptions = async (page: playwright.Page): Promise<string[]> => {
    if (this.scrapingConfig.dateOptionsSelector) {
      return this.scraper.getValues(page, this.scrapingConfig.dateOptionsSelector)
    }
    throw new Error(`No selector provided for date options`)
  }

  getAllLinksOnPage = async (page: playwright.Page): Promise<string[]> => {
    if (this.scrapingConfig.detailPageButtonSelector) {
      return this.scraper.getLinks(page, this.scrapingConfig.detailPageButtonSelector)
    }
    throw new Error(`No selector provided for links`)
  }

  getLinksAcrossPages = async (page: playwright.Page, allPageLinks?: string[], allScrapedLinks?: string[]): Promise<string[]> => {
    var pageLinks = allPageLinks ?? []
    var scrapedLinks = allScrapedLinks ?? []

    return this.getAllLinksOnPage(page)
      .then((links: string[]) => {
        scrapedLinks.push(...links)
        return this.getNextPageLink(page)
      })
      .then((link: string) => {
        if (!pageLinks.includes(link)) {
          pageLinks.push(link)
          return this.navigateToUrl(page, link)
        }
        throw new Error("Page is already in the link list. Breaking loop")
      })
      .then((page: playwright.Page) => this.getLinksAcrossPages(page, pageLinks, scrapedLinks))
      .catch((error) => {
        console.warn(error)
        return scrapedLinks
      })
  }

  selectDateOption = async (page: playwright.Page, option?: string): Promise<playwright.Page> => {
    return this.elementInteractor.select(page, this.scrapingConfig.dateSelectSelector, option)
  }

  scrapeDetailPage = async (page: playwright.Page): Promise<Show> => {
    return this.showScraper.scapeShow(page)
  }

  navigateToUrl = async (page: playwright.Page, input?: string): Promise<playwright.Page> => {
    if (input) return page.goto(input).then(() => page)
    return providedPromiseResponse(page)
  }

  expandPage = async (page: playwright.Page): Promise<playwright.Page> => {
    if (this.scrapingConfig.moreShowsButtonSelector) {
      return this.elementInteractor.clickPageButton(page, this.scrapingConfig.moreShowsButtonSelector)
        .then((page: playwright.Page) => this.expandPage(page))
        .catch((error) => {
          console.warn(error)
          return page
        })
    }
    return providedPromiseResponse(page)
  }

  getNextPageLink = (page: playwright.Page): Promise<string> => {
    if (this.scrapingConfig.nextPageLinkSelector) {
      return this.scraper.getLink(page, this.scrapingConfig.nextPageLinkSelector);
    }
    throw new Error(`No page link on ${page.url()}`)
  }


}