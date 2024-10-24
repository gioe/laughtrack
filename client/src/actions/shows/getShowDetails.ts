'use server'

import { auth } from "@/auth";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { ShowInterface } from "@/interfaces/show.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { Session } from "next-auth";

export interface GetShowDetailsParams extends FilterParams { }

export interface GetShowDetailsResponse {
  entity: ShowInterface;
}

export async function getShowDetails(id: string) {

  const getClubDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_SHOW_DETAILS + `/${id}`

  return auth()
    .then((session: Session | null) => {
      return fetch(getClubDetailsUrl, {
        method: "GET",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? ''
        },
      });
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}