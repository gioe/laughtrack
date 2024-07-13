import { SCRAPER_KEYS } from "../constants/objects.js";

export class Club {
  name: string;
  scrapedPage: string;

  constructor(jsonModel: any) {
    this.name = jsonModel[SCRAPER_KEYS.name]
    this.scrapedPage = jsonModel[SCRAPER_KEYS.scrapedPage]
  }

}