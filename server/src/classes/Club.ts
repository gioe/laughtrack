import { SCRAPER_KEYS } from "../constants/objects.js";
import {  ClubHTMLConfiguration, ComedianHTMLConfiguration, HTMLConfigurable, ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";

export class Club implements HTMLConfigurable {

  /* 
  {
  "name": "Comedy Cellar New York",
  "baseWebsite": "https://www.comedycellar.com",
  "schedulePage": "/new-york-line-up/",
  "timezone": "America/New_York"
  }
  */

  json: any;

  name: string;
  baseWebsite: string;
  schedulePage: string;
  timezone: string;
  scrapedPage: string;

  clubConfig: ClubHTMLConfiguration;
  showConfig: ShowHTMLConfiguration;
  comedianConfig: ComedianHTMLConfiguration;

  constructor(json: any) {
    this.json = json;

    this.clubConfig = json[SCRAPER_KEYS.clubConfig]
    this.showConfig = json[SCRAPER_KEYS.showConfig]
    this.comedianConfig = json[SCRAPER_KEYS.comedianConfig]

    this.name = json[SCRAPER_KEYS.name];
    this.baseWebsite = json[SCRAPER_KEYS.baseWebsite];
    this.schedulePage = json[SCRAPER_KEYS.schedulePage];
    this.timezone = json[SCRAPER_KEYS.timezone];
    this.scrapedPage = this.baseWebsite + this.schedulePage;
    
  }
  
}