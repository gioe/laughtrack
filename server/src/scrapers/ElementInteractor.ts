import puppeteer from 'puppeteer';
import { ElementScaper } from './ElementScaper.js';
import { delay} from "../util/types/promiseUtil.js";

export class ElementInteractor {

  private elementScraper = new ElementScaper();

  selectOption = async (option: string, 
    selector: string, 
    page: puppeteer.Page,
    providedDelay: number): Promise<unknown> => {
    
      return page.select(selector, option)
      .then(() => delay(providedDelay))
  }

  navigateToUrl = async (url: string, 
    page: puppeteer.Page,
    providedDelay: number): Promise<unknown> => {
    return page.goto(url)
      .then(() => delay(providedDelay))
  }

  expandPage = async (basePage: puppeteer.Page, selector: string): Promise<puppeteer.Page> => {
    return selector !== "" ? this.expandIfPossible(basePage, selector) : basePage;
  }

  private expandIfPossible = async (page: puppeteer.Page, selector: string): Promise<puppeteer.Page> => {
    return this.elementScraper.getElementCount(page, selector)
      .then((count: number) => count == 0 ? page : this.clickExpander(page, selector));
  }

  private clickExpander = async (page: puppeteer.Page, selector: string): Promise<puppeteer.Page> => {
    return page.click(selector)
      .then(() => page.waitForSelector(selector))
      .then(() => this.expandIfPossible(page, selector))
      .catch((error) => page)
  }

}