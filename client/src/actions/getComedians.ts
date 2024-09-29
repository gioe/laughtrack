'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getComedians() {
  const allComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.COMEDIANS

  return fetch(allComediansUrl, {
    cache: 'no-store',
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data)
      return data
    })
    .catch((error) => console.log(error))
}