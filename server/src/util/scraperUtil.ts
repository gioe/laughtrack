import playwright from "playwright";
import { 
  ScrapingLoopFunction,
  InteractionFunction, 
  LoopProviderFunction, 
  ScrapingFunction 
} from "../@types/scrapingFunction.js";
import { Scrapable } from "../api/interfaces/scrapable.interface.js";
import { ShowInterface } from "../api/interfaces/show.interface.js";

export const generateScrapingLoop = async (
  page: playwright.Page, 
  loopProviderFunction: LoopProviderFunction,
  action: InteractionFunction, 
  scrapingFunction: ScrapingFunction | ScrapingLoopFunction): Promise<ShowInterface[]> => {

    return loopProviderFunction(page)
    .then((loopValues: any[]) => {
      return runInteractionLoop(page, 
        loopValues,   
        action,
        scrapingFunction)
    })
}

export const runInteractionLoop = async (
  page: playwright.Page, 
  inputs: any[], 
  action: InteractionFunction,
  scrapingFunction: ScrapingFunction | ScrapingLoopFunction): Promise<ShowInterface[]> => {

  var scrapedShows: ShowInterface[] = [];

  for (let index = 0; index < inputs.length - 1; index++) {
    const input = inputs[index];
    const shows = await actThenScrape(action(page, input), input, scrapingFunction)
    scrapedShows = scrapedShows.concat(shows)
  }
  
  return scrapedShows
  
}

export const actThenScrape = async (pageResponse: Promise<playwright.Page>,
  input: any,
  scrape: ScrapingFunction | ScrapingLoopFunction
): Promise<ShowInterface[]> => {
  return pageResponse.then((scrapable: Scrapable) => scrape(scrapable, input))
}
