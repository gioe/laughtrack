'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { auth } from "../../auth"
import { MEDIUM_ELEMENT_PAGE_REQUEST_SIZE } from "@/lib/contants";

export interface FetchComedianParams {
  page?: string,
  query?: string
}

export interface GetComediansResponse {
  comedians: ComedianInterface[]
  totalPages: number;
  totalComedians: number;
}

export async function getComedians(params?: FetchComedianParams) {
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