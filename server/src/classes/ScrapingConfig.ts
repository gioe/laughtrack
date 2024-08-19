import { SCRAPER_KEYS } from "../constants/objects.js";

export class ScrapingConfig {

  pagesToScrape?: number;
  dateOptionsSelector?: string;
  dateSelectSelector?: string;

  showDetailContainerSelector?: string;
  detailPageButtonSelector?: string;
  nextPageLinkSelector?: string;

  validShowContainerSignifier?: string;
  showDetailPageLinkSelector?: string;
  dateTimeSelector?: string;
  dateSelector?: string;
  showTimeSelector?: string;
  dateSeparator?: string;
  showTicketLinkSelector?: string;
  invalidLinkText?: string;

  badDateStrings?: string[];
  badTimeStrings?: string[];
  comedianNameSelector?: string;
  badNameCharacters?: string[];
  badNameStrings?: string[];
  showSignifiers?: string[];
  requiredSelectors?: string[];


  constructor(json: any) {
    this.pagesToScrape = json[SCRAPER_KEYS.pagesToScrape];
    this.dateOptionsSelector = json[SCRAPER_KEYS.dateOptionsSelector];
    this.dateSelectSelector = json[SCRAPER_KEYS.dateSelectSelector];

    this.showDetailContainerSelector = json[SCRAPER_KEYS.showDetailContainerSelector];
    this.detailPageButtonSelector = json[SCRAPER_KEYS.detailPageButtonSelector];

    this.validShowContainerSignifier = json[SCRAPER_KEYS.validShowContainerSignifier];
    this.showDetailPageLinkSelector = json[SCRAPER_KEYS.showDetailPageLinkSelector];
    this.nextPageLinkSelector = json[SCRAPER_KEYS.nextPageLinkSelector]

    this.dateTimeSelector = json[SCRAPER_KEYS.dateTimeSelector];
    this.dateSelector = json[SCRAPER_KEYS.dateSelector];
    this.showTimeSelector = json[SCRAPER_KEYS.showTimeSelector];
    this.dateSeparator = json[SCRAPER_KEYS.dateSeparator];
    this.showTicketLinkSelector = json[SCRAPER_KEYS.showTicketLinkSelector];
    this.badDateStrings = json[SCRAPER_KEYS.badDateStrings];
    this.badTimeStrings = json[SCRAPER_KEYS.badTimeStrings];
    this.comedianNameSelector = json[SCRAPER_KEYS.comedianNameSelector];
    this.badNameCharacters = json[SCRAPER_KEYS.badNameCharacters];
    this.badNameStrings = json[SCRAPER_KEYS.badNameStrings];
    this.showSignifiers = json[SCRAPER_KEYS.showSignifiers];
    this.requiredSelectors = json[SCRAPER_KEYS.requiredSelectors];
    this.invalidLinkText = json[SCRAPER_KEYS.invalidLinkText];
  }

}

