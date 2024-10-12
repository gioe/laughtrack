import { ClubInterface } from "../../../models/interfaces/club.interface.js";

interface ClubFilter {
  city?: string;
  name?: string;
}

export const filterClubs = (clubs: ClubInterface[], filter: ClubFilter): ClubInterface[] => {
  return clubs.filter((club: ClubInterface) => {
    const nameMatches = filter.name ? club.name.toLowerCase().includes(filter.name.toLowerCase()) : true;
    const cityMatches = filter.city ? club.city.toLowerCase() == filter.city.toLowerCase() : true;

    return nameMatches && cityMatches
  })
}