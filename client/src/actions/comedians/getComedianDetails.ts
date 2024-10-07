'use server'

import { auth } from "@/auth";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"

const PAGE_SIZE = '20';

export interface GetComedianDetailsParams {
  name: string;
  query?: string
  currentPage?: string
}

export interface GetComedianDetailsResponse {
  comedian: ComedianInterface
  totalPages: number;
}

export async function getComedianDetails(params: GetComedianDetailsParams) {

  const comedianDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_COMEDIAN_DETAILS + `/${params.name}`

  return auth()
  .then((session: any) => {
    return fetch(comedianDetailsUrl, {
      cache: 'no-store',
      method: "GET",
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'x-auth-token': session.accessToken ?? ''
      },
    });
  })
  .then((response) => response.json())
  .then((data) => data)
  .catch((error) => console.log(error))

}