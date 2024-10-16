'use server'

import { auth } from "@/auth";
import { ShowInterface } from "@/interfaces/show.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"

export interface GetShowDetailsParams {
  sort?: string;
  query?: string
  page?: string
}

export interface GetShowDetailsResponse {
  entity: ShowInterface;
}

export async function getShowDetails(id: string, params: GetShowDetailsParams) {

  const getClubDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_SHOW_DETAILS + `/${id}`

  return auth()
  .then((session: any) => {
    return fetch(getClubDetailsUrl, {
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