'use server'

import { auth } from "@/auth";
import { ClubInterface } from "@/interfaces/club.interface";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { Session } from "next-auth";

export interface GetClubDetailsParams extends FilterParams { }

export interface GetClubDetailsResponse {
  entity: ClubInterface;
}

export async function getClubDetails(id: string, params: GetClubDetailsParams) {

  const getClubDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_CLUB_DETAILS + `/${id}`

  return auth()
    .then((session: Session | null) => {
      return fetch(getClubDetailsUrl, {
        method: "GET",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? '',
          'sort': params.sort ?? "date",
          'query': params.query ?? "",
          'page': params?.page ?? "0",
          'rows': params.rows ?? "10"
        },
      });
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}