'use server'

import { auth } from "@/auth";
import { ClubInterface } from "@/interfaces/club.interface";
import { MEDIUM_ELEMENT_PAGE_REQUEST_SIZE } from "@/lib/contants";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { date } from "zod"

export interface GetClubDetailsParams {
  id: string;
  sort?: string;
  query?: string
  page?: string
}

export interface GetClubDetailsResponse {
  entity: ClubInterface;
  totalPages: number;
}

export async function getClubDetails(params: GetClubDetailsParams) {

  const getClubDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_CLUB_DETAILS + `/${params.id}`
  
  return auth()
  .then((session: any) => {
    return fetch(getClubDetailsUrl, {
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