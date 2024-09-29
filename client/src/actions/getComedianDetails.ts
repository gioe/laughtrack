'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface"
import { PUBLIC_ROUTES } from "@/lib/routes"

const PAGE_SIZE = '20';


export async function getComedianDetails(name: string) {

  const comedianDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.COMEDIAN_DETAILS
  
  return fetch(comedianDetailsUrl, {
    cache: 'no-store',
    method: "POST",
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams({
      name
    }),
  })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}