import puppeteer from 'puppeteer';
import { runTasks } from '../util/types/promiseUtil.js';
import { ElementScaper } from './ElementScaper.js';
import { LINKS } from '../constants/links.js';

export class ShowContainerScraper {

  private elementScraper = new ElementScaper();

  getShowLinks = async (page: puppeteer.Page,
    showLinkContainerSelector: string,
    validSignifierSelector: string,
    showPageLinkSelector: string, 
  ): Promise<string[]> => {
    
    return this.getShowLinkContainers(page, showLinkContainerSelector)
    .then((elements: puppeteer.ElementHandle<Element>[]) => this.filterInvalidElements(elements, [validSignifierSelector, showPageLinkSelector]))
    .then((validatedValues: (puppeteer.ElementHandle<Element> | undefined)[]) => validatedValues.filter((value) =>  value !== undefined) as puppeteer.ElementHandle<Element>[])
    .then((finalElements: puppeteer.ElementHandle<Element>[]) => this.getAllUrls(finalElements, showPageLinkSelector))
    .then((links: string[]) => links.filter((link: string) => !LINKS.badLinks.includes(link)))
    
  }

  getShowLinkContainers = async (page: puppeteer.Page,
    showLinkContainerSelector: string
  ): Promise<puppeteer.ElementHandle<Element>[]>  => {
    return this.elementScraper.getElementCount(page, showLinkContainerSelector)
    .then((count: number) => count > 0 ? this.elementScraper.getAllElementsHandlersFrom(page, showLinkContainerSelector) : [])
  }

  filterInvalidElements = async (elements: puppeteer.ElementHandle<Element>[], 
    requiredSelectors: string[]) => {
      const tasks = elements.map((element) => this.elementScraper.validateElements(element, requiredSelectors))
      return runTasks(tasks)
    }

  getAllUrls = async (elements: puppeteer.ElementHandle<Element>[], 
    showPageLinkSelector: string): Promise<string[]> => {
      const tasks = elements.map((element) => this.elementScraper.getHrefFrom(element, showPageLinkSelector))      
      return runTasks(tasks)
  }

}