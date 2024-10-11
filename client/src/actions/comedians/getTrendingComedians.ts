'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getTrendingComedians() {
  const trendingComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_TRENDING_COMEDIANS

  return fetch(trendingComediansUrl, {
    cache: 'no-store',
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}