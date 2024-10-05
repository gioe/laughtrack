'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"
import { date } from "zod"


export async function getClubDetails(name: string) {

  const clubDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.CLUB_DETAILS + `/${name}`

  console.log(clubDetailsUrl)
  
  return fetch(clubDetailsUrl, {
    cache: 'no-store',
    method: "GET",
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  })
    .then((response) => response.json())
    .then((data) =>  {
      console.log(data)
      return data
    })
    .catch((error) => console.log(error))
}