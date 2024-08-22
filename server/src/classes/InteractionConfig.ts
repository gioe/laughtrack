import { INTERACTION_KEYS } from "../constants/objects.js";
import { ScraperType } from "../types/ScraperType.js";

export class InteractionConfig {

  moreShowsButtonSelector: string;
  showDetailContainerSelector: string;
  
  scraperType: ScraperType;

  constructor(json: any) {
    this.moreShowsButtonSelector = json[INTERACTION_KEYS.moreShowsButtonSelector];
    this.showDetailContainerSelector = json[INTERACTION_KEYS.showDetailContainerSelector];

    this.scraperType = json[INTERACTION_KEYS.scraperType];
  }

}
