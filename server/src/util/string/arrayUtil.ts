import { Comedian } from "../../types/comedian.interface.js";

export function upsertComedian(array: Comedian[], comedian: Comedian) {
    // Find the index of the comedian in the array
    const index = array.findIndex((e) => e.name === comedian.name);
  
    // If the element exists, update it
    if (index !== -1) {
      const existingShow = array[index].shows;
      array[index] = {
        ...array[index],
        shows: existingShow.concat(comedian.shows)
      };
    } else {
      // If the comedian does not exist, add it to the array
      array.push(comedian);
    }
    return array
  }