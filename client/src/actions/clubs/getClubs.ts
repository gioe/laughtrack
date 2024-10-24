'use server'

import { auth } from "@/auth";
import { ClubInterface } from "@/interfaces/club.interface";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { Session } from "next-auth";

export interface GetClubsParams extends FilterParams {
  city?: string,
}

export interface GetClubsResponse {
  clubs: ClubInterface[]
  totalClubs: number;
  cities: string[]
}

export async function getClubs(params?: GetClubsParams) {

  const getClubsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_ALL_CLUBS

  return auth()
    .then((session: Session | null) => {
      return fetch(getClubsUrl, {
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? ''
        },
        body: new URLSearchParams({
          query: params?.query ?? "",
          sort: params?.sort ?? "date",
          page: params?.page ?? "0",
          city: params?.city ?? "",
          rows: params?.rows ?? "10"
        }),
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}