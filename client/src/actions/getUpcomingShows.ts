'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"

const PAGE_SIZE = '20';

interface SearchResultsParams {
  currentPage: string;
  location: string;
  startDate: string;
  endDate: string;
}

export async function getUpcomingShowResults(params: SearchResultsParams) {

  const trendingComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.HOME_SEARCH
  
  return fetch(trendingComediansUrl, {
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
      pageSize: PAGE_SIZE
    }),
  })
    .then((response) => response.json())
    .then((data: any) => data)
    .catch((error) => console.log(error))
}