import { Comedian } from "../../classes/Comedian.js"
import { TextConfigurable } from "../../types/textConfigurable.interface.js";
import { isLikelyShow } from "./showUtil.js";
import { removeSubstrings } from "./stringUtil.js";

const PARENTHESIS_REGEX = /\(([^()]+)\)/g;
const SEPARATOR = ",";

export const  cleanFinalComedianList = (comedianArray: Comedian[]): Comedian[] => {
    const allComicNames = comedianArray
      .filter((comedian: Comedian) => comedian.name !== "")
      .map((comedian: Comedian) => comedian.name)

    return []
  }

  export const cleanNameString = (nameString: string, textConfig: TextConfigurable): string => {

    if (!isLikelyShow(nameString, textConfig.showSignifiers)) {
      return ""
    }

    const assumedCredits: string[] = nameString.match(PARENTHESIS_REGEX) ?? []
    
    const valuesToRemove = assumedCredits
      .concat(textConfig.badCharacters)
      .concat(textConfig.badWords);

    const cleanedString = removeSubstrings(nameString, valuesToRemove)
      .replaceAll(textConfig.commaPlacement, SEPARATOR);
    const splitstinrg = cleanedString.split(SEPARATOR);

    return ""
  }