'use server'

import { SearchResult } from "@/interfaces/searchResult.interface"
import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getUpcomingShowResults(data: any) {

  const trendingComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.SEARCH_SHOWS

  return fetch(trendingComediansUrl, {
    cache: 'no-store',
    method: "POST",
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams({
      location: data.location,
      startDate: data.startDate,
      endDate: data.endDate
    }),
  })
    .then((response) => response.json())
    .then((data: SearchResult[]) => data)
    .catch((error) => console.log(error))
}