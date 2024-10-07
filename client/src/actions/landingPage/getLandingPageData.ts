'use server'

import { getCities } from "../cities/getCities";
import { getTrendingClubs } from "../clubs/getTrendingClubs";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { getTrendingComedians } from "../comedians/getTrendingComedians";

export interface LandingPageResponseInterface {
  trendingComedians: ComedianInterface[]
  cities: string[];
}

export async function getLandingPageData() {
  
  return Promise.all([getCities(), getTrendingComedians()]).then((responses: any[]) => {
    console.log(responses[1])
    return {
      cities: responses[0],
      trendingComedians: responses[1],
    } as LandingPageResponseInterface

  })
  
}