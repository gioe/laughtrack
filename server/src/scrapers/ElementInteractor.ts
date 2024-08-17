import playwright, { ElementHandle } from "playwright";
import { delay, provideGenericPromiseResponse } from "../util/types/promiseUtil.js";

const INTERACTION_DELAY = 1000;

export class ElementInteractor {

  select = async (page: playwright.Page,
    selector?: string,
    option?: string): Promise<playwright.Page> => {

    if (selector && option) {
      return page.selectOption(selector, option)
        .then(() => delay(INTERACTION_DELAY))
        .then(() => page)
    }
    return provideGenericPromiseResponse(page)
  }

  clickPageButton = async (page: playwright.Page,
    selector?: string): Promise<playwright.Page> => {
    
    if (selector) {
      return page.click(selector)
        .then(() => delay(INTERACTION_DELAY))
        .then(() => page)
    }  
    return provideGenericPromiseResponse(page)
  }

}