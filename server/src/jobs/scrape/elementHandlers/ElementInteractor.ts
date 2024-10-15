import playwright from "playwright-core";
import { delay, providedPromiseResponse } from "../../../common/util/promiseUtil.js";
import { ScrapableScraper } from "../scrapers/ScrapableScraper.js";

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
    return providedPromiseResponse(page)
  }

  clickPageButton = async (page: playwright.Page,
    selector: string): Promise<playwright.Page> => {

      return this.scrapableScraper.getElementVisibility(page, selector)
      .then((visible: boolean) => {
        if (visible) return page.locator(selector).click()
        throw new Error("Button not visible. No reason to try to click.")
      })
      .then(() => delay(INTERACTION_DELAY))
      .then(() => page)
    }


}