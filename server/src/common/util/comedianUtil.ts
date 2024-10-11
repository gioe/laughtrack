import { REGEX } from "../constants/regex.js";
import { ComedianInterface } from "../interfaces/client/comedian.interface.js";
import { Comedian } from "../models/Comedian.js";
import { ScrapingConfig } from "../models/ScrapingConfig.js";
import { isLikelyShow } from "./showUtil.js";
import { removeSubstrings } from "./stringUtil.js";

const SEPARATOR = ",";

export const buildComediansFromNames = (comedianNames: string[], config: ScrapingConfig): Comedian[] => {

  return comedianNames
  .map((comedianName: string) => normalizeNameString(comedianName, config))
  .flatMap((names: string[]) => names.map((name: string) => new Comedian(name)))
}

  export const normalizeNameString = (nameString: string, config: ScrapingConfig): string[] => {
    const cleanedString = cleanNameString(nameString, config);

    if (isLikelyShow(cleanedString, config.showSignifiers)) {
      console.warn(`${nameString} is probably a show and not a comedian name`)
      return []
    }
  
    return likelyContainsMultipleComedians(cleanedString) ? cleanedString.split(SEPARATOR) : [nameString]
  }

  const cleanNameString = (nameString: string, config: ScrapingConfig): string => {
    const badContent = combineBadContent(nameString, config)
    return removeSubstrings(nameString, badContent ?? [])
    ;
  }

  const combineBadContent = (nameString: string, config: ScrapingConfig) => {
    var credits = nameString.match(REGEX.parenthesis) as string[] ?? [];
    credits = credits.concat(config.badNameCharacters ?? [])
    credits = credits.concat(config.badNameStrings ?? [])
    return credits
  }

  const likelyContainsMultipleComedians = (nameString: string): boolean => {

    // Does the name have commas?
    const includesCommas = nameString.includes(SEPARATOR)

    // Does the name contain more spaces than a single name should?
    const spaceCount = nameString.match(" ")?.length ?? 0

    return includesCommas || spaceCount > 3
  }

  export const sortComedians = (comedians: ComedianInterface[], sortValue?: string): ComedianInterface[] => {
    return comedians.sort((a: ComedianInterface, b: ComedianInterface) => {
      if (sortValue == 'alphabetical') return a.name < b.name ? -1 : 1;
      else return (b.socialData?.popularityScore ?? 0) - (a.socialData?.popularityScore ?? 0)
    })
  }