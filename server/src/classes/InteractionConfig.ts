import { INTERACTION_KEYS } from "../constants/objects.js";
import PageInteractable from "../types/pageInteractable.interface.js";
import { ScraperType } from "../types/scraperTypes.js";

export class InteractionConfig implements PageInteractable {

  moreShowsButtonSelector: string;
  showDetailContainerSelector: string;
  nextPageLinkSelector: string;
  
  scraperType: ScraperType;

  constructor(json: any) {
    this.moreShowsButtonSelector = json[INTERACTION_KEYS.moreShowsButtonSelector];
    this.showDetailContainerSelector = json[INTERACTION_KEYS.showDetailContainerSelector];
    this.nextPageLinkSelector = json[INTERACTION_KEYS.nextPageLinkSelector];

    this.scraperType = json[INTERACTION_KEYS.scraperType];
  }

}
