'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { auth } from "../auth"

const PAGE_SIZE = '20';

export interface GetComediansResponse {
  comedians: ComedianInterface[]
  query: string;
  totalPages: number;
}

export async function fetchFavoriteComedians(currentPage: string, query: string) {
  const favoriteComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.ALL_FAVORITE_COMEDIANS

  return auth()
    .then((session: any) => {
      return fetch(favoriteComediansUrl, {
        cache: 'no-store',
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session.accessToken ?? ''
        },
        body: new URLSearchParams({
          page: currentPage,
          query: query,
          pageSize: PAGE_SIZE
        }),
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}