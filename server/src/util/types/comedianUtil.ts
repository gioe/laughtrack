import { Comedian } from "../../classes/Comedian.js"
import { REGEX } from "../../constants/regex.js";
import { ComedianHTMLConfiguration } from "../../types/htmlconfigurable.interface.js";
import { Show } from "../../types/show.interface.js";
import { isLikelyShow } from "./showUtil.js";
import { removeSubstrings, replaceSubstrings } from "./stringUtil.js";

const SEPARATOR = ",";

export const buildComediansFromNames = (comedianNames: string[], comedianConfig: ComedianHTMLConfiguration) => {

  return comedianNames
  .map((comedianName: string) => normalizeNameString(comedianName, comedianConfig))
  .flatMap((names: string[]) => names.map((name: string) => new Comedian(name)))
  
}

  export const normalizeNameString = (nameString: string, comedianConfig: ComedianHTMLConfiguration): string[] => {
    const cleanedString = cleanNameString(nameString, comedianConfig);

    if (isLikelyShow(cleanedString, comedianConfig.showSignifiers ?? [])) {
      console.warn(`${nameString} is a likely show that needs fixing`)
      return []
    }
  
    return likelyContainsMultipleComedians(cleanedString) ? cleanedString.split(SEPARATOR) : [nameString]
  }

  const cleanNameString = (nameString: string, comedianConfig: ComedianHTMLConfiguration): string => {
    var cleanedString = nameString

    cleanedString = removeCredits(cleanedString)
    cleanedString = removeBadConfigContent(cleanedString, comedianConfig)
    cleanedString = replaceSubstrings(cleanedString, comedianConfig.commaPlacements ?? [], SEPARATOR)

    return cleanedString;
  }

  const removeCredits = (nameString: string): string => {
    const credits = nameString.match(REGEX.parenthesis) ?? [];
    return removeSubstrings(nameString, credits)
  }

  const removeBadConfigContent = (nameString: string, comedianConfig: ComedianHTMLConfiguration): string => {
    const badContent = comedianConfig.badNameCharacters?.concat(comedianConfig.badNameStrings ?? [])
    return removeSubstrings(nameString, badContent ?? [])
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