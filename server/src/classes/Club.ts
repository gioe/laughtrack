import { CLUB_KEYS } from "../constants/objects.js";

export class Club {
  name: string;
  scrapedPage: string;
  homePage: string;

  constructor(jsonModel: any) {
    this.name = jsonModel[CLUB_KEYS.name]
    this.scrapedPage = jsonModel[CLUB_KEYS.scrapedPage]
    this.homePage = jsonModel[CLUB_KEYS.homePage]
  }

}