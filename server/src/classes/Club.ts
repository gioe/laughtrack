import { SCRAPER_KEYS } from "../constants/objects.js";
import { ClubHTMLConfiguration, ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";

export class Club {

  /* 
  {
  "name": "Comedy Cellar New York",
  "baseWebsite": "https://www.comedycellar.com",
  "schedulePage": "/new-york-line-up/",
  }
  */

  json: any;

  name: string;
  baseWebsite: string;
  schedulePage: string;

  dateOptionsSelector: string;
  showLinkContainerSelector: string;
  dateMenuSelector: string;
  allShowElementsSelector: string;
  showPageLinkSelector: string;
  expansionSelector: string;
  validShowContainerSignifier: string;
  showDateTimeSelector: string;
  showTimeSelector: string;
  showDateSelector: string;
  scrapedPage: string;

  requiresSelectingDates: boolean;
  requiresNavigatingToShowLinks: boolean;
  shouldScrapeShowDatetime: boolean;

  clubConfig: ClubHTMLConfiguration;
  showConfig: ShowHTMLConfiguration;

  constructor(json: any) {
    this.json = json;
    this.clubConfig = json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.clubConfig]
    this.showConfig = json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.showConfig]

    this.dateOptionsSelector = this.clubConfig.dateOptionsSelector ?? "";
    this.showLinkContainerSelector = this.clubConfig.showLinkContainerSelector ?? "";
    this.dateMenuSelector = this.clubConfig.dateMenuSelector ?? "";
    this.allShowElementsSelector = this.clubConfig.allShowElementsSelector ?? "";
    this.showPageLinkSelector = this.clubConfig.showPageLinkSelector ?? "";
    this.expansionSelector = this.clubConfig.expansionSelector ?? "";
    this.validShowContainerSignifier = this.clubConfig.validShowContainerSignifier ?? "";

    this.showDateTimeSelector = this.showConfig.showDateTimeSelector ?? "";
    this.showTimeSelector = this.showConfig.showTimeSelector ?? "";
    this.showDateSelector = this.showConfig.showDateSelector ?? "";

    this.name = json[SCRAPER_KEYS.name];
    this.baseWebsite = json[SCRAPER_KEYS.baseWebsite];
    this.schedulePage = json[SCRAPER_KEYS.schedulePage];
    this.scrapedPage = this.baseWebsite + this.schedulePage;

    this.requiresSelectingDates = this.clubConfig.shouldScapeByDates;
    this.requiresNavigatingToShowLinks = this.clubConfig.shouldScrapeByShows;
    this.shouldScrapeShowDatetime = this.showConfig.showDateTimeSelector != undefined;
  }
  
}