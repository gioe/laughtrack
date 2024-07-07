import { Comedian } from "../../classes/Comedian.js";
import { Show } from "../../types/show.interface.js";
import { TextConfigurable } from "../../types/textConfigurable.interface.js";
import { isLikelyShow } from "./showUtil.js";
import { removeSubstrings } from "./stringUtil.js";

// Finds us whatever text is between parentheses, which we assume represent the comedian's credits.
const PARENTHESIS_REGEX = /\(([^()]+)\)/g;
const SEPARATOR = ",";

export const buildComedianFromScrapedElements = (comedianNames: string[], 
  textConfig: TextConfigurable,
  show: Show): Comedian[] => {

  return comedianNames
  .map((comedianName: string) => cleanNameString(comedianName, textConfig))
  .filter((cleanedString: string) => !isLikelyShow(cleanedString, textConfig.showSignifiers))
  .flatMap((cleanedString: string) => cleanedString.split(SEPARATOR))
  .map((actualName: string) => buildComedian(actualName, show))

}

export const cleanNameString = (nameString: string, textConfig: TextConfigurable): string => {
  const assumedCredits: string[] = nameString.match(PARENTHESIS_REGEX) ?? []

  const valuesToRemove = assumedCredits
  .concat(textConfig.badCharacters)
  .concat(textConfig.badWords);
  
  return removeSubstrings(nameString, valuesToRemove)
  .replaceAll(textConfig.commaPlacement, SEPARATOR);
}

export const buildComedian = (name: string, show: Show): Comedian => {
  const comedian = new Comedian(name, "");
  comedian.addShow(show)
  return comedian
}

export const flattenComedians = (comedianArrays: Comedian[][]): Comedian[] => {
  return comedianArrays.flatMap((array: Comedian[]) => array)
}

export const cleanComedianList = (comedianArray: Comedian[]): Comedian[] => {
  console.log(comedianArray.length)

  const prunedArray = comedianArray
  .filter((comedian: Comedian) => comedian.name !== "")
  console.log(prunedArray.length)

  const namesOnly = comedianArray.map((comedian: Comedian) => comedian.name)

  let uniqueElements = [...new Set(namesOnly)];
  console.log(uniqueElements.length)

  return []

}



