import { ClubInterface } from "../../../models/interfaces/club.interface.js";

  export const sortClubs = (clubs: ClubInterface[], sortValue?: string): ClubInterface[] => {
    return clubs.sort((a: ClubInterface, b: ClubInterface) => {
      if (sortValue == 'alphabetical') return a.name < b.name ? -1 : 1;
      else return (b.popularityScore ?? 0) - (a.popularityScore ?? 0)
    })
  }