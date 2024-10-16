'use server'

import { ComedianFilterInterface, ComedianInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { auth } from "../../auth"

export interface GetAllComedianFiltersResponse {
  filters: ComedianFilterInterface[]
}

export async function getAllComedianFilters() {
  const getAllComedianFilters = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_ALL_COMEDIAN_FILTERS

  return auth()
    .then((session: any) => {
      return fetch(getAllComedianFilters, {
        cache: 'no-store',
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session.accessToken ?? ''
        }
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}