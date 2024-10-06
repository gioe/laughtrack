'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"

const PAGE_SIZE = '20';


export async function getComedianDetails(name: string) {

  const comedianDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.COMEDIAN_DETAILS + `/${name}`
  
  return fetch(comedianDetailsUrl, {
    cache: 'no-store',
    method: "GET",
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
  })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}