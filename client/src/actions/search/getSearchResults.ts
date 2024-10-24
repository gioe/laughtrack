'use server'

import { auth } from "@/auth";
import { CityInterface } from "@/interfaces/city.interface";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { ShowProviderInterface } from "@/interfaces/showProvider.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { Session } from "next-auth";

export interface HomeSearchParams extends FilterParams {
  location: string;
  startDate: string;
  endDate: string;
  clubs?: string;
}

export interface HomeSearchResultResponse extends ShowProviderInterface {
  entity: CityInterface;
  clubs: string[];
  totalShows: number
}

export async function getSearchResults(params: HomeSearchParams) {

  const upcomingShowsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.HOME_SEARCH

  return auth()
    .then((session: Session | null) => {
      return fetch(upcomingShowsUrl, {
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? ''
        },
        body: new URLSearchParams({
          location: params.location,
          startDate: params.startDate,
          endDate: params.endDate,
          sort: params.sort ?? "date",
          clubs: params.clubs ?? "",
          query: params.query ?? "",
          page: params.page ?? "0",
          rows: params.rows ?? "10"
        }),
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}