'use server'

import { ComedianFilterInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { auth } from "../../auth"
import { Session } from "next-auth";

export interface GetAllComedianFiltersResponse {
  filters: ComedianFilterInterface[]
}

export async function getAllComedianFilters() {
  const getAllComedianFilters = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_ALL_COMEDIAN_FILTERS

  return auth()
    .then((session: Session | null) => {
      return fetch(getAllComedianFilters, {
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? ''
        }
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}