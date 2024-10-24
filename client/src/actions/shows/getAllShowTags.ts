'use server'

import { auth } from "@/auth";
import { TagInterface } from "@/interfaces/tag.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { Session } from "next-auth";

export interface GetAllShowTagsReponse {
  tags: TagInterface[];
}

export async function getAllShowTags() {

  const getClubDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_SHOW_TAGS

  return auth()
    .then((session: Session | null) => {
      return fetch(getClubDetailsUrl, {
        method: "GET",
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'x-auth-token': session?.accessToken ?? ''
        },
      });
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))

}