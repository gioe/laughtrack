'use server'

import { auth } from "@/auth";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { Session } from "next-auth";

export interface GetComedianDetailsParams extends FilterParams { }

export interface GetComedianDetailsResponse {
  entity: ComedianInterface
  totalShows: number;
}

export async function getComedianDetails(id: string, params: GetComedianDetailsParams) {

  const comedianDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_COMEDIAN_DETAILS + `/${id}`
  return auth()
    .then((session: Session | null) => {
      return fetch(comedianDetailsUrl, {
        method: "GET",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? '',
          'sort': params.sort ?? "date",
          'page': params?.page ?? "0",
          'rows': params?.rows ?? "10"
        },
      });
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}