'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getCities() {
  const trendingClubsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.CITIES

  return fetch(trendingClubsUrl, {
    cache: 'no-store',
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => {
      return data.map((object: any) => object.city)
    })
    .catch((error) => console.log(error))
}