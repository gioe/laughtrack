'use server'

import { auth } from "@/auth";
import { ClubInterface } from "@/interfaces/club.interface";
import { MEDIUM_ELEMENT_PAGE_REQUEST_SIZE } from "@/lib/contants";
import { PUBLIC_ROUTES } from "@/lib/routes"

export interface GetClubsParams {
  city?: string,
  page?: string,
  query?: string
  sort?: string
}

export interface GetClubsResponse {
  clubs: ClubInterface[]
  totalPages: number;
  totalClubs: number;
  cities: string[]
}

export async function getClubs(params?: GetClubsParams) {

  const getClubsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_ALL_CLUBS

  return auth()
    .then((session: any) => {
      return fetch(getClubsUrl, {
        cache: 'no-store',
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session.accessToken ?? ''
        },
        body: new URLSearchParams({
          query: params?.query ?? "",
          sort: params?.sort ?? "",
          page: params?.page ?? "1",
          city: params?.city ?? "",
          pageSize: MEDIUM_ELEMENT_PAGE_REQUEST_SIZE
        }),
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}