import playwright from "playwright";
import { delay, provideGenericPromiseResponse } from "../util/promiseUtil.js";
import { ElementCounter } from "./ElementCounter.js";
import { ScrapableScraper } from "./ScrapableScraper.js";

const INTERACTION_DELAY = 1000;

export class ElementInteractor {

  private scrapableScraper = new ScrapableScraper();

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
        return this.scrapableScraper.getElementVisibility(page, selector)
        .then((visible: boolean) => {
          if (visible) return page.click(selector)
          throw new Error("Button not visible. No reason to try to click.")
        })
        .then(() => delay(INTERACTION_DELAY))
        .then(() => page)

      }
      return provideGenericPromiseResponse(page)
    }


}