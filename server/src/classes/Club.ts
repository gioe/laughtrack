import { SCRAPER_KEYS } from "../constants/objects.js";

export class Club {

  /* 
  {
  "name": "Comedy Cellar New York",
  "baseWebsite": "https://www.comedycellar.com",
  "schedulePage": "/new-york-line-up/",
  }
  */ 

  json: any;
  
  constructor(json: any) {
    this.json = json;
  }

  getName = () => {
    return this.json[SCRAPER_KEYS.name]
  }
    
  getBaseWebsite = () => {
    return this.json[SCRAPER_KEYS.baseWebsite]
  }

  getSchedulePage = () => {
    return this.json[SCRAPER_KEYS.schedulePage]
  }

  getScrapedPage = () => {
    return this.getBaseWebsite() + this.getSchedulePage()
  }

}