'use server'

import { auth } from "@/auth";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { Session } from "next-auth";

export interface UpdateFavoriteStateParams {
  id?: number;
  isFavorite: boolean;
}

export async function updateFavoriteState(params: UpdateFavoriteStateParams) {
  const favoritesEndpoint = process.env.URL_DOMAIN + PUBLIC_ROUTES.FAVORITE_COMEDIAN + `/${params.id ?? 0}`

  return auth()
    .then((session: Session | null) => {
      return fetch(favoritesEndpoint, {
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? ''
        },
        body: new URLSearchParams({
          isFavorite: params.isFavorite ? "1" : "0"
        }),
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}