'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"

export async function addToFavorites(id: number, isFavorite: boolean, token?: string) {
  const favoritesEndpoint = process.env.URL_DOMAIN + PUBLIC_ROUTES.FAVORITE_COMEDIAN + `/${id ?? 0}`

  return fetch(favoritesEndpoint, {
    cache: 'no-store',
    method: "POST",
    headers: {
      'x-auth-token': token ?? ''
    },
    body: new URLSearchParams({
      isFavorite: isFavorite ? "1" : "0"
    }),
  })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}