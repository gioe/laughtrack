import puppeteer from 'puppeteer';
import { delay, provideGenericPromiseResponse} from "../util/types/promiseUtil.js";
import Interactable from '../types/interactable.interface.js';
import { InteractableElement } from '../types/scrapingFunction.js';

const INTERACTION_DELAY = 1000;

export class ElementInteractor {

  select = async (interactable: InteractableElement, 
    selector?: string,
    option?: string): Promise<puppeteer.Page> => {
      if (option && selector) {
        return (interactable as Interactable).select(selector, option)
        .then(() => delay(INTERACTION_DELAY))
        .then(() => interactable as puppeteer.Page)
      }

      return provideGenericPromiseResponse(interactable as puppeteer.Page)
  }

  click = async (interactable: InteractableElement, 
    selector?: string): Promise<puppeteer.Page> => {

    if (selector) {
      return (interactable as Interactable).click(selector)
      .then(() => (interactable as Interactable).waitForSelector(selector))
      .then(() => delay(INTERACTION_DELAY))
      .then(() => interactable as puppeteer.Page)
    }

    return provideGenericPromiseResponse(interactable as puppeteer.Page)
  }

}