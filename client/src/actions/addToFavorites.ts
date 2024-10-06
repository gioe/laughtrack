'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"

export async function addToFavorites(id: number | undefined) {
  const trendingClubsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.FAVORITE_COMEDIAN + `/${id ?? 0}`

  return fetch(trendingClubsUrl, {
    cache: 'no-store',
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) =>  data.map((object: any) => object.city))
    .catch((error) => console.log(error))
}