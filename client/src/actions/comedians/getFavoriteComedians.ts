'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { auth } from "../../auth"
import { LineupItem } from "@/interfaces/lineupItem.interface";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { Session } from "next-auth";

export interface FetchFavoriteComedianParams extends FilterParams {}

export interface GetComediansResponse {
  comedians: ComedianInterface[] | LineupItem[]
  query?: string;
}

export async function getFavoriteComedians(params?: FetchFavoriteComedianParams) {
  const favoriteComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_FAVORITE_COMEDIANS

  return auth()
    .then((session: Session | null) => {
      return fetch(favoriteComediansUrl, {
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? ''
        },
        body: new URLSearchParams({
          query: params?.query ?? "",
          page: params?.page ?? "0",
          rows: params?.rows ?? "10",
        }),
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}