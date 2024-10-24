'use server'

import { auth } from "@/auth";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { MEDIUM_ELEMENT_PAGE_REQUEST_SIZE } from "@/lib/contants";
import { PUBLIC_ROUTES } from "@/lib/routes"

export interface GetComedianDetailsParams extends FilterParams { }

export interface GetComedianDetailsResponse {
  entity: ComedianInterface
  totalShows: number;
}

export async function getComedianDetails(id: string, params: GetComedianDetailsParams) {

  const comedianDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_COMEDIAN_DETAILS + `/${id}`
  return auth()
    .then((session: any) => {
      return fetch(comedianDetailsUrl, {
        cache: 'no-store',
        method: "GET",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session.accessToken ?? '',
          'page': params?.page ?? "1",
          'rows': params?.rows ?? MEDIUM_ELEMENT_PAGE_REQUEST_SIZE,
          'sort': params.sort ?? "date_time"
        },
      });
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}