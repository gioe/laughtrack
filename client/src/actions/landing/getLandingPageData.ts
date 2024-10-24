'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface";
import { getCities } from "../cities/getCities";
import { getTrendingComedians } from "../comedians/getTrendingComedians";

export interface LandingPageResponseInterface {
  trendingComedians: ComedianInterface[]
  cities: string[];
}

export async function getLandingPageData() {

  return Promise.all([getCities(), getTrendingComedians()]).then((responses) => {

    return {
      cities: responses[0],
      trendingComedians: responses[1],
    } as LandingPageResponseInterface

  })

}