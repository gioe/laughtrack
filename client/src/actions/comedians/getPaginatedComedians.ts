'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { auth } from "../../auth"
import { MEDIUM_ELEMENT_PAGE_REQUEST_SIZE } from "@/lib/contants";

export interface FetchPaginatedComedianParams {
  page?: string
  query?: string
  sort?: string
}

export interface GetPaginatedComediansResponse {
  comedians: ComedianInterface[]
  totalPages: number;
  totalComedians: number;
}

export async function getPaginatedComedians(params?: FetchPaginatedComedianParams) {
  const allComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_ALL_COMEDIANS

  return auth()
    .then((session: any) => {
      return fetch(allComediansUrl, {
        cache: 'no-store',
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session.accessToken ?? ''
        },
        body: new URLSearchParams({
          sort: params?.sort ?? 'popularity',
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