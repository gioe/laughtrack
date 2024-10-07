'use server'

import { auth } from "@/auth";
import { ClubInterface } from "@/interfaces/club.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"

const PAGE_SIZE = '20';

export interface GetClubsParams {
  currentPage?: string,
  query?: string
}

export interface GetClubsResponse {
  clubs: ClubInterface[]
  query: string;
  totalPages: number;
}

export async function getClubs(params: GetClubsParams) {

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
          page: params?.currentPage ?? "1",
          pageSize: PAGE_SIZE
        }),
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}