import { SCRAPER_KEYS } from "../constants/objects.js";

export class ScrapingConfig {

  pagesToScrape?: number;
  optionsSelector?: string;
  showDetailContainerSelector?: string;
  validShowContainerSignifier?: string;
  showDetailPageLinkSelector?: string;
  dateTimeSelector?: string;
  dateSelector?: string;
  timeSelector?: string;
  dateSeparator?: string;
  ticketLinkSelector?: string;
  badDateStrings?: string[];
  badTimeStrings?: string[];
  nameSelector?: string;
  badNameCharacters?: string[];
  badNameStrings?: string[];
  showSignifiers?: string[];
  requiredSelectors?: string[];
  invalidLinkText?: string;


  constructor(json: any) {
    this.pagesToScrape = json[SCRAPER_KEYS.pagesToScrape];
    this.optionsSelector = json[SCRAPER_KEYS.optionsSelector];
    this.showDetailContainerSelector = json[SCRAPER_KEYS.showDetailContainerSelector];
    this.validShowContainerSignifier = json[SCRAPER_KEYS.validShowContainerSignifier];
    this.showDetailPageLinkSelector = json[SCRAPER_KEYS.showDetailPageLinkSelector];
    this.dateTimeSelector = json[SCRAPER_KEYS.dateTimeSelector];
    this.dateSelector = json[SCRAPER_KEYS.dateSelector];
    this.timeSelector = json[SCRAPER_KEYS.timeSelector];
    this.timeSelector = json[SCRAPER_KEYS.timeSelector];
    this.dateSeparator = json[SCRAPER_KEYS.dateSeparator];
    this.ticketLinkSelector = json[SCRAPER_KEYS.ticketLinkSelector];
    this.badDateStrings = json[SCRAPER_KEYS.badDateStrings];
    this.badTimeStrings = json[SCRAPER_KEYS.badTimeStrings];
    this.nameSelector = json[SCRAPER_KEYS.nameSelector];
    this.badNameCharacters = json[SCRAPER_KEYS.badNameCharacters];
    this.badNameStrings = json[SCRAPER_KEYS.badNameStrings];
    this.showSignifiers = json[SCRAPER_KEYS.showSignifiers];
    this.requiredSelectors = json[SCRAPER_KEYS.requiredSelectors];
    this.invalidLinkText = json[SCRAPER_KEYS.invalidLinkText];
  }

}

