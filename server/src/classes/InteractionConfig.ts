import { INTERACTION_KEYS } from "../constants/objects.js";
import PageInteractable from "../types/pageInteractable.interface.js";

export class InteractionConfig implements PageInteractable {

  moreShowsButtonSelector: string;
  showDetailContainerSelector: string;
  nextPageLinkSelector: string;
  
  shouldScrapeByOptionSelection: string;
  shouldScrapeByDetailPage: string;
  shouldScrapeByNavigationAndDetailPages: string;
  optionsSelector: string;
  selectSelector?: string;

  constructor(json: any) {
    this.moreShowsButtonSelector = json[INTERACTION_KEYS.moreShowsButtonSelector];
    this.showDetailContainerSelector = json[INTERACTION_KEYS.showDetailContainerSelector];
    this.nextPageLinkSelector = json[INTERACTION_KEYS.nextPageLinkSelector];

    this.shouldScrapeByOptionSelection = json[INTERACTION_KEYS.shouldScrapeByOptionSelection];
    this.shouldScrapeByDetailPage = json[INTERACTION_KEYS.shouldScrapeByDetailPage];
    this.shouldScrapeByNavigationAndDetailPages = json[INTERACTION_KEYS.shouldScrapeByNavigationAndDetailPages];
    this.optionsSelector = json[INTERACTION_KEYS.optionsSelector];
    this.selectSelector = json[INTERACTION_KEYS.selectSelector];
  }

}
