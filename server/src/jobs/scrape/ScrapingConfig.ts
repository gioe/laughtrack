import { SCRAPER_KEYS } from "../../common/util/constants/keys.js";

export class ScrapingConfig {

  dateTimeSeparator?: string;
  dateOptionsSelector?: string;
  dateSelectSelector?: string;
  detailPageButtonSelector?: string;
  linkContainer?: string;
  nextPageLinkSelector?: string;
  showContainerSelector?: string;
  moreShowsButtonSelector?: string;
  dateTimeContainer?: string;
  dateTimeSelector?: string;
  showTicketLinkSelector?: string;
  dateSelector?: string;
  timeSelector?: string;
  comedianNameSelector?: string;
  showNameSelector?: string;
  eventbriteDateTimeSelector?: string;
  eventbriteShowNameSelector?: string;
  eventbriteComedianNameSelector?: string;
  priceSelector?: string;

  constructor(json: any) {
    this.dateTimeSeparator = json[SCRAPER_KEYS.dateTimeSeparator]
    this.dateOptionsSelector = json[SCRAPER_KEYS.dateOptionsSelector];
    this.dateSelectSelector = json[SCRAPER_KEYS.dateSelectSelector];
    this.detailPageButtonSelector = json[SCRAPER_KEYS.detailPageButtonSelector];
    this.linkContainer = json[SCRAPER_KEYS.linkContainer];
    this.moreShowsButtonSelector = json[SCRAPER_KEYS.moreShowsButtonSelector];
    this.nextPageLinkSelector = json[SCRAPER_KEYS.nextPageLinkSelector]
    this.dateTimeSelector = json[SCRAPER_KEYS.dateTimeSelector];
    this.dateTimeContainer = json[SCRAPER_KEYS.dateTimeContainer];
    this.timeSelector = json[SCRAPER_KEYS.timeSelector];
    this.dateSelector = json[SCRAPER_KEYS.dateSelector];
    this.comedianNameSelector = json[SCRAPER_KEYS.comedianNameSelector];
    this.showNameSelector = json[SCRAPER_KEYS.showNameSelector];
    this.eventbriteDateTimeSelector = json[SCRAPER_KEYS.eventbriteDateTimeSelector];
    this.eventbriteShowNameSelector = json[SCRAPER_KEYS.eventbriteShowNameSelector];
    this.eventbriteComedianNameSelector = json[SCRAPER_KEYS.eventbriteComedianNameSelector];
    this.priceSelector = json[SCRAPER_KEYS.priceSelector]
    this.showContainerSelector = json[SCRAPER_KEYS.showContainerSelector]
    this.showTicketLinkSelector = json[SCRAPER_KEYS.showTicketLinkSelector]
  }

}

