'use server'

import { PUBLIC_ROUTES } from "@/lib/routes"
import { date } from "zod";

const PAGE_SIZE = '20';

export async function getClubDetails(name: string) {

  const clubDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.CLUB_DETAILS
  
  return fetch(clubDetailsUrl, {
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
    .then((data) =>  data)
    .catch((error) => console.log(error))
}