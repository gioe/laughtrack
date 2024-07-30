import puppeteer from "puppeteer";
import { ElementScaper } from "./ElementScaper.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { buildComediansFromNames } from "../util/types/comedianUtil.js";
import { ComedianHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { Comedian } from "../classes/Comedian.js";

export class ComedianScraper {
  private json: any;
  private elementScraper = new ElementScaper();

  constructor(
    json: any,
  ) {
    this.json = json;
  }

  private comedianHtmlConfig = (): ComedianHTMLConfiguration => {
    return this.json[SCRAPER_KEYS.htmlConfig][SCRAPER_KEYS.comedianConfig];
  }

  private allComedianNameSelector = () => {
    return this.comedianHtmlConfig().allComedianNameSelector ?? "";
  }

  getAllComedianNames = async (showComponent: puppeteer.ElementHandle<Element>): Promise<string[]> => {
    return this.elementScraper.getElementCount(showComponent, this.allComedianNameSelector())
      .then((count: number) => count > 0 ? this.elementScraper.getAllTextContentFrom(showComponent, this.allComedianNameSelector()) : [])
  }

  getAllComedians = async (showComponent: puppeteer.ElementHandle<Element>): Promise<Comedian[]> => {
    return this.getAllComedianNames(showComponent)
      .then((names: string[]) => {
        return buildComediansFromNames(names, this.comedianHtmlConfig())
      })
  }

}
