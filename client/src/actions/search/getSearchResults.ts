'use server'

import { auth } from "@/auth";
import { ShowProviderInterface } from "@/interfaces/dateContainer.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"

const PAGE_SIZE = '20';

export interface HomeSearchParams {
  location: string;
  startDate: string;
  endDate: string;
  sort?: string;
  currentPage?: string;
}

export interface HomeSearchResultResponse extends ShowProviderInterface {
  city: string;
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
        sort: params.sort ?? "date_time",
        page: params.currentPage ?? "1",
        pageSize: PAGE_SIZE
      }),
    })
  })
  .then((response) => response.json())
  .then((data) => data)
  .catch((error) => console.log(error))
  
}