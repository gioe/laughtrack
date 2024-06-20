import { Comedian } from "../../classes/Comedian.js";

export function upsertComedian(array: Comedian[], comedian: Comedian) {
  // Find the index of the comedian in the array
  const index = array.findIndex((e) => e.name === comedian.name);

  // If the element exists, update it
  if (index !== -1) {
    array[index].addShows(comedian.shows)
  } else {
    array.push(comedian);
  }

}