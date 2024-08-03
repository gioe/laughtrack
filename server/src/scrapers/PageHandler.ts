import puppeteer from 'puppeteer';
import { ElementInteractor } from './ElementInteractor.js';
import { ElementScaper } from './ElementScaper.js';
import { provideGenericPromiseResponse } from '../util/types/promiseUtil.js';

export class PageHandler {

  private elementInteractor = new ElementInteractor();
  private elementScraper = new ElementScaper();

  buildRootPage = async (browser: puppeteer.Browser,  destination: string): Promise<puppeteer.Page> => {
    return browser.newPage()
      .then((page: puppeteer.Page) => page.goto(destination).then(() => page));
  }

  expandPageIfPossible = async (page: puppeteer.Page, moreShowsSelector?: string): Promise<puppeteer.Page> => {

    if (moreShowsSelector) {
      return this.elementScraper.getElementCount(page, moreShowsSelector)
      .then((count: number) =>  {
        if (count == 0) {
          return page 
        } else {
          return this.elementInteractor.clickExpander(page, moreShowsSelector)
        }
      })
      .then((page: puppeteer.Page) => this.expandPageIfPossible(page, moreShowsSelector))
      .catch(() => page)
    } 
    return provideGenericPromiseResponse(page)
  }

  navigateToUrl = async (url: string, page: puppeteer.Page,delay: number): Promise<unknown> => {
    return this.elementInteractor.navigateToUrl(url, page, delay)
  }

  selectOption = async (page: puppeteer.Page,
     delay: number, 
     dateOption?: string, 
     selector?: string): Promise<unknown> => {    
    return this.elementInteractor.selectOption(page, delay, dateOption, selector)
  }

}