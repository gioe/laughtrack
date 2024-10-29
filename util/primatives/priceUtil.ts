import { REGEX } from "../constants/regex";
import { removeBadWhiteSpace } from "./stringUtil";

export function toPrice(priceString: string): string {
  var cleanedString = priceString;

  if (containsPriceRange(priceString)) {
    cleanedString = priceString.split("-")[0]
  }

  if (cleanedString.includes("$")) {
    cleanedString = getPriceByRegex(cleanedString) ?? "$0";
    cleanedString = cleanedString.replaceAll("$", "")
    cleanedString = removeBadWhiteSpace(cleanedString);
  }
  
  const number = Number(cleanedString)
  return (Math.round(number * 100) / 100).toFixed(2);
}

function containsPriceRange(priceString: string): boolean {
  return priceString.includes("-")
}

export const getPriceByRegex = (priceString: string): string | undefined =>  {
  const priceValues = priceString.match(REGEX.price);
  return priceValues ? priceValues[0] as string : undefined
}
