import playwright from "playwright-core";
import { Show } from "../models/classes/Show.js";
import {
  InteractionFunction,
  LoopProviderFunction,
  ScrapingFunction
} from "../models/@types/ScrapingFunctions.js";

export const generateScrapingLoop = async (
  page: playwright.Page,
  loopProviderFunction: LoopProviderFunction,
  action: InteractionFunction,
  scrapingFunction: ScrapingFunction): Promise<Show[]> => {

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
  scrapingFunction: ScrapingFunction): Promise<Show[]> => {
  
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
  scrape: ScrapingFunction
): Promise<Show> => {
  return pageResponse.then((page: playwright.Page) => scrape(page, input))
}
