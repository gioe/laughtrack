'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"

const PAGE_SIZE = '20';

interface SearchResultsParams {
  currentPage: string;
  location: string;
  startDate: string;
  endDate: string;
  filter: string;
}

export async function getSearchResults(params: SearchResultsParams) {

  const upcomingShowsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.HOME_SEARCH

  return fetch(upcomingShowsUrl, {
    cache: 'no-store',
    method: "POST",
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams({
      location: params.location,
      startDate: params.startDate,
      endDate: params.endDate,
      page: params.currentPage,
      pageSize: PAGE_SIZE,
      filter: params.filter
    }),
  })
    .then((response) => response.json())
    .then((data: any) => data)
    .catch((error) => console.log(error))
}