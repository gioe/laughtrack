import playwright from "playwright-core";
import { 
  ScrapingLoopFunction,
  InteractionFunction, 
  LoopProviderFunction, 
} from "../@types/ScrapingFunctions.js";
import { ScrapingFunction } from "../@types/ScrapingFunctions.js";
import { Show } from "../models/Show.js";
import { Scrapable } from "../interfaces/client/scrape.interface.js";

export const generateScrapingLoop = async (
  page: playwright.Page, 
  loopProviderFunction: LoopProviderFunction,
  action: InteractionFunction, 
  scrapingFunction: ScrapingFunction | ScrapingLoopFunction): Promise<Show[]> => {

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
  scrapingFunction: ScrapingFunction | ScrapingLoopFunction): Promise<Show[]> => {

  var scrapedShows: Show[] = [];

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
): Promise<Show[]> => {
  return pageResponse.then((scrapable: Scrapable) => scrape(scrapable, input))
}
