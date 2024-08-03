import { Comedian } from "../../classes/Comedian.js"
import { REGEX } from "../../constants/regex.js";
import { ComedianHTMLConfiguration } from "../../types/htmlconfigurable.interface.js";
import { Show } from "../../types/show.interface.js";
import { isLikelyShow } from "./showUtil.js";
import { removeSubstrings } from "./stringUtil.js";

const SEPARATOR = ",";

export const buildComediansFromNames = (comedianNames: string[], comedianConfig: ComedianHTMLConfiguration) => {

  return comedianNames
  .map((comedianName: string) => normalizeNameString(comedianName, comedianConfig))
  .flatMap((names: string[]) => names.map((name: string) => new Comedian(name)))
}

  export const normalizeNameString = (nameString: string, comedianConfig: ComedianHTMLConfiguration): string[] => {
    const cleanedString = cleanNameString(nameString, comedianConfig);

    if (isLikelyShow(cleanedString, comedianConfig.showSignifiers)) {
      console.warn(`${nameString} is probably a show and not a comedian name`)
      return []
    }
  
    return likelyContainsMultipleComedians(cleanedString) ? cleanedString.split(SEPARATOR) : [nameString]
  }

  const cleanNameString = (nameString: string, comedianConfig: ComedianHTMLConfiguration): string => {
    const badContent = combineBadContent(nameString, comedianConfig)
    return removeSubstrings(nameString, badContent ?? [])
    ;
  }

  const combineBadContent = (nameString: string, comedianConfig: ComedianHTMLConfiguration) => {
    var credits = nameString.match(REGEX.parenthesis) as string[] ?? [];
    credits = credits.concat(comedianConfig.badNameCharacters ?? [])
    credits = credits.concat(comedianConfig.badNameStrings ?? [])
    return credits
  }

  const likelyContainsMultipleComedians = (nameString: string): boolean => {

    // Does the name have commas?
    const includesCommas = nameString.includes(SEPARATOR)

    // Does the name contain more spaces than a single name should?
    const spaceCount = nameString.match(" ")?.length ?? 0

    return includesCommas || spaceCount > 3
  }
  
  export const cleanFinalComedianList = (comedianArray: Comedian[]): Comedian[] => {
    const allComicNames = getUniqueNames(comedianArray);
    return allComicNames.map((name: string) => createMergedComics(name, comedianArray))
  }

  const createMergedComics = (name: string, comedianArray: Comedian[]) => {
    const containerComic = new Comedian(name)

      comedianArray.forEach((comedian: Comedian) => {
        if (comedian.name === name) {
          comedian.shows.forEach((show: Show) => {
            containerComic.addShow(show)
          })
        }
      })
      return containerComic;
  }

  const getUniqueNames = (comedianArray: Comedian[]) => {
    const allComicNames = comedianArray
    .filter((comedian: Comedian) => comedian.name !== "")
    .map((comedian: Comedian) => comedian.name)   
    return  [...new Set(allComicNames)]
  }