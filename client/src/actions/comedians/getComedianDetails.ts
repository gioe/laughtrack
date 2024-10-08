'use server'

import { auth } from "@/auth";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { MEDIUM_ELEMENT_PAGE_REQUEST_SIZE } from "@/lib/contants";
import { PUBLIC_ROUTES } from "@/lib/routes"

export interface GetComedianDetailsParams {
  id: string;
  sort?: string;
  query?: string
  page?: string
}

export interface GetComedianDetailsResponse {
  entity: ComedianInterface
  totalPages: number;
}

export async function getComedianDetails(params: GetComedianDetailsParams) {

  const comedianDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_COMEDIAN_DETAILS + `/${params.id}`
  return auth()
  .then((session: any) => {
    return fetch(comedianDetailsUrl, {
      cache: 'no-store',
      method: "GET",
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'x-auth-token': session.accessToken ?? '',
        'page': params?.page ?? "1",
        'pageSize': MEDIUM_ELEMENT_PAGE_REQUEST_SIZE,
        'sort': params.sort ?? "date_time"
      },
    });
  })
  .then((response) => response.json())
  .then((data) => data)
  .catch((error) => console.log(error))

}