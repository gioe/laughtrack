'use server'

import { auth } from "@/auth";
import { ClubInterface } from "@/interfaces/club.interface";
import { LARGE_ELEMENT_PAGE_REQUEST_SIZE, MEDIUM_ELEMENT_PAGE_REQUEST_SIZE } from "@/lib/contants";
import { PUBLIC_ROUTES } from "@/lib/routes"

export interface GetClubDetailsParams {
  sort?: string;
  query?: string
  page?: string
}

export interface GetClubDetailsResponse {
  entity: ClubInterface;
  totalPages: number;
}

export async function getClubDetails(id: string, params: GetClubDetailsParams) {

  const getClubDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_CLUB_DETAILS + `/${id}`

  console.log(params)
  return auth()
  .then((session: any) => {
    return fetch(getClubDetailsUrl, {
      cache: 'no-store',
      method: "GET",
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'x-auth-token': session.accessToken ?? '',
        'page': params?.page ?? "1",
        'sort': params.sort ?? "date", 
        'query': params.query ?? "",
        'pageSize': LARGE_ELEMENT_PAGE_REQUEST_SIZE
      },
    });
  })
  .then((response) => response.json())
  .then((data) => data)
  .catch((error) => console.log(error))

}