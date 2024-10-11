'use server'

import { auth } from "@/auth";
import { CityInterface } from "@/interfaces/city.interface";
import { ShowProviderInterface } from "@/interfaces/dateContainer.interface";
import { LARGE_ELEMENT_PAGE_REQUEST_SIZE } from "@/lib/contants";
import { PUBLIC_ROUTES } from "@/lib/routes"

export interface HomeSearchParams {
  location: string;
  startDate: string;
  endDate: string;
  sort?: string;
  page?: string;
  clubs?: string;
  query?: string
}

export interface HomeSearchResultResponse extends ShowProviderInterface {
  entity: CityInterface;
  clubs: string[];
  totalPages: number
  totalShows: number
}

export async function getSearchResults(params: HomeSearchParams) {

  const upcomingShowsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.HOME_SEARCH

  return auth()
  .then((session: any) => {
    return fetch(upcomingShowsUrl, {
      cache: 'no-store',
      method: "POST",
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'x-auth-token': session.accessToken ?? ''
      },
      body: new URLSearchParams({
        location: params.location,
        startDate: params.startDate,
        endDate: params.endDate,
        sort: params.sort ?? "date",
        clubs: params.clubs ?? "",
        query: params.query ?? "",
        page: params.page ?? "1",
        pageSize: LARGE_ELEMENT_PAGE_REQUEST_SIZE
      }),
    })
  })
  .then((response) => response.json())
  .then((data) => data)
  .catch((error) => console.log(error))
  
}