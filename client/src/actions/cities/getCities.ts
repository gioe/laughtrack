'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getCities() {
  const getCitiesUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_CITIES

  return fetch(getCitiesUrl, {
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}