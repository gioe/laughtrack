import { ElementScaper } from "./ElementScaper.js";
import { buildComediansFromNames } from "../util/types/comedianUtil.js";
import { Comedian } from "../classes/Comedian.js";
import { Club } from "../classes/Club.js";
import Scrapable from "../types/scrapable.interface.js";

export class ComedianScraper {
  private club: Club;
  private elementScraper = new ElementScaper();

  constructor(
    club: Club,
  ) {
    this.club = club;
  }

  getAllComedians = async (showComponent: Scrapable): Promise<Comedian[]> => {
    return this.getAllComedianNames(showComponent)
      .then((names: string[]) => {
        return buildComediansFromNames(names, this.club.comedianConfig)
      })
  }

  getAllComedianNames = async (showComponent: Scrapable): Promise<string[]> => {
    return this.elementScraper.getElementCount(showComponent, this.club.comedianConfig.nameSelector)
      .then((count: number) => count > 0 ? this.elementScraper.getAllTextContentFrom(showComponent, this.club.comedianConfig.nameSelector) : [])
  }

}
