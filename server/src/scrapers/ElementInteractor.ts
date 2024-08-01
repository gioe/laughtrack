import puppeteer from 'puppeteer';
import { ElementScaper } from './ElementScaper.js';
import { delay, emptyStringPromise, emptyUndefinedPromise, provideGenericPromiseResponse} from "../util/types/promiseUtil.js";

export class ElementInteractor {

  private elementScraper = new ElementScaper();


  selectOption = async (page: puppeteer.Page,
    providedDelay: number,
    option?: string, 
    selector?: string): Promise<unknown> => {

      if (option && selector) {
        return page.select(selector, option)
        .then(() => delay(providedDelay))
      }

      return emptyUndefinedPromise()
  }

  navigateToUrl = async (url: string, 
    page: puppeteer.Page,
    providedDelay: number): Promise<unknown> => {
    return page.goto(url)
      .then(() => delay(providedDelay))
  }

  clickExpander = async (page: puppeteer.Page, selector?: string): Promise<puppeteer.Page> => {

    if (selector) {
      return page.click(selector)
      .then(() => page.waitForSelector(selector))
      .then(() => page)
    }
    return provideGenericPromiseResponse(page)
  }

}