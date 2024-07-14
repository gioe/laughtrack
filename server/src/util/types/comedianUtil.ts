import { Comedian } from "../../classes/Comedian.js"
import { Show } from "../../types/show.interface.js";
import { TextConfigurable } from "../../types/textConfigurable.interface.js";
import { isLikelyShow } from "./showUtil.js";
import { removeSubstrings, replaceSubstrings } from "./stringUtil.js";

const PARENTHESIS_REGEX = /\(([^()]+)\)/g;
const SEPARATOR = ",";

  export const normalizeNameString = (nameString: string, textConfig: TextConfigurable): string[] => {
    const cleanedString = cleanNameString(nameString, textConfig);
    
    if (isLikelyShow(cleanedString, textConfig.showSignifiers)) {
      console.warn(`${cleanedString} is a likely show that needs fixing`)
      return []
    }

    return likelyContainsMultipleComedians(cleanedString) ? cleanedString.split(SEPARATOR) : [nameString]

  }

  const cleanNameString = (nameString: string, textConfig: TextConfigurable): string => {
    var cleanedString = nameString

    cleanedString = removeCredits(cleanedString)
    cleanedString = removeBadConfigContent(cleanedString, textConfig)
    cleanedString = replaceSubstrings(cleanedString, textConfig.commaPlacements, SEPARATOR)

    return cleanedString;
  }

  const removeCredits = (nameString: string): string => {
    const credits = nameString.match(PARENTHESIS_REGEX) ?? [];
    return removeSubstrings(nameString, credits)
  }

  const removeBadConfigContent = (nameString: string, textConfig: TextConfigurable): string => {
    const badContent = textConfig.badCharacters.concat(textConfig.badWords)
    return removeSubstrings(nameString, badContent)
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

      if (containerComic.name === 'Joe List') {
        containerComic.shows.forEach((show: Show) => {
          console.log(show)
        })
      }

      return containerComic;
  }

  const getUniqueNames = (comedianArray: Comedian[]) => {
    const allComicNames = comedianArray
    .filter((comedian: Comedian) => comedian.name !== "")
    .map((comedian: Comedian) => comedian.name)   
    return  [...new Set(allComicNames)]
  }