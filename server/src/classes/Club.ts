import { CLUB_KEYS } from "../constants/objects.js";
import { ScrapingConfig } from "./ScrapingConfig.js";

export class Club {

  /* 
  {
  "name": "Comedy Cellar New York",
  "baseWebsite": "https://www.comedycellar.com",
  "schedulePage": "/new-york-line-up/",
  "timezone": "America/New_York"
  }
  */


  name: string;
  baseUrl: string;
  schedulePageUrl: string;
  timezone: string;

  constructor(json: any) {
    this.name = json[CLUB_KEYS.name];
    this.baseUrl = json[CLUB_KEYS.baseUrl];
    this.schedulePageUrl = json[CLUB_KEYS.schedulePageUrl];
    this.timezone = json[CLUB_KEYS.timezone];
  }

  buildCompleteFromLink = (link: string) => {
    return this.baseUrl + link;
  }

}