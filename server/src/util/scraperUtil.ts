import playwright from "playwright";
import { 
  ScrapingLoopFunction,
  InteractionFunction, 
  LoopProviderFunction, 
  ScrapingFunction 
} from "../types/scrapingFunction.js";
import { Comedian } from "../classes/Comedian.js";
import { Scrapable } from "../api/interfaces/scrapable.interface.js";

export const generateScrapingLoop = async (
  page: playwright.Page, 
  loopProviderFunction: LoopProviderFunction,
  action: InteractionFunction, 
  scrapingFunction: ScrapingFunction | ScrapingLoopFunction) => {

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
  scrapingFunction: ScrapingFunction | ScrapingLoopFunction): Promise<Comedian[][]> => {

  var comedianArrays: Comedian[][] = [];

  console.log(`Looping through ${inputs.length} elements`)

  for (let index = 0; index < inputs.length - 1; index++) {
    const comedians = await actThenScrape(action(page, inputs[index]), scrapingFunction)
    comedianArrays = comedianArrays.concat(comedians)
  }
  
  return comedianArrays
  
}

export const actThenScrape = async (pageResponse: Promise<playwright.Page>,
  scrape: ScrapingFunction | ScrapingLoopFunction
): Promise<Comedian[][]> => {
  return pageResponse.then((scrapable: Scrapable) => scrape(scrapable))
}
