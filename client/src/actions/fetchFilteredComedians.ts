'use server'

import { ComedianInterface } from "@/interfaces/comedian.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { getSession } from "next-auth/react";
import { auth } from "../auth"

const PAGE_SIZE = '20';

export interface GetComediansResponse {
  comedians: ComedianInterface[]
  query: string;
  totalPages: number;
}

export async function fetchFilteredComedians(currentPage: string, query: string) {
  const allComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.COMEDIANS
  return auth()
    .then((session: any) => {
      return fetch(allComediansUrl, {
        cache: 'no-store',
        method: "POST",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session.accessToken ?? ''
        },
        body: new URLSearchParams({
          page: currentPage,
          query: query,
          pageSize: PAGE_SIZE
        }),
      })
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}