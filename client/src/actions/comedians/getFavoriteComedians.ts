'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { auth } from "../../auth"
import { MEDIUM_ELEMENT_PAGE_REQUEST_SIZE } from "@/lib/contants";

export interface FetchFavoriteComedianParams {
  query?: string;
  page?: string;
}

export interface GetComediansResponse {
  comedians: ComedianInterface[]
  query?: string;
  totalPages: number;
}

export async function getFavoriteComedians(params?: FetchFavoriteComedianParams) {
  const favoriteComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_FAVORITE_COMEDIANS

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
          query: params?.query ?? "", 
          page: params?.page ?? "1",
          pageSize: MEDIUM_ELEMENT_PAGE_REQUEST_SIZE
        }),
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}