'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface"
import { PUBLIC_ROUTES } from "@/lib/routes"

const PAGE_SIZE = '20';

export interface GetComediansResponse {
  comedians: ComedianInterface[]
  totalPages: number;
}

export async function getComedians(currentPage: string) {
  const allComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.COMEDIANS

  return fetch(allComediansUrl, {
    cache: 'no-store',
    method: "POST",
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams({
      page: currentPage,
      pageSize: PAGE_SIZE
    }),
  })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}