'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { auth } from "../../auth"
import { FilterParams } from "@/interfaces/filterParams.interface";
import { Session } from "next-auth";

export interface FetchPaginatedComedianParams extends FilterParams {}

export interface GetPaginatedComediansResponse {
  comedians: ComedianInterface[]
  totalComedians: number;
}

export async function getPaginatedComedians(params?: FetchPaginatedComedianParams) {
  const allComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_ALL_COMEDIANS

  return auth()
    .then((session: Session | null) => {
      return fetch(allComediansUrl, {
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? ''
        },
        body: new URLSearchParams({
          sort: params?.sort ?? 'popularity',
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