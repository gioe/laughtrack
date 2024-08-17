import playwright from "playwright";
import { InteractionFunction, ScrapableElement, ScrapingFunction } from "../../types/scrapingFunction.js";
import { Comedian } from "../../classes/Comedian.js";
import { Scrapable } from "../../types/scrapable.interface.js";

export const runInteractionLoop = async (page: playwright.Page, 
  inputs: any[], 
  interactionFunction: InteractionFunction, 
  scrapingFunction: ScrapingFunction): Promise<Comedian[][]> => {

  var comedianArrays: Comedian[][] = [];

  console.log(`Looping through ${inputs.length} elements`)

  for (let index = 0; index < inputs.length - 1; index++) {
    const comedians = await interactAndScrape(page, inputs[index], interactionFunction, scrapingFunction)
    comedianArrays = comedianArrays.concat(comedians)
  }
  
  return comedianArrays
  
}

export const interactAndScrape = async (page: playwright.Page, 
  input: any,
  interactionFunction: InteractionFunction, 
  scrapingFunction: ScrapingFunction
): Promise<Comedian[][]> => {
  return interactionFunction(page, input)
  .then((scrapable: Scrapable) => scrapingFunction(scrapable))
}
