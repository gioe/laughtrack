import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getTrendingComics() {
    const trendingComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.TRENDING_COMEDIANS
    return fetch(trendingComediansUrl, {
      method: "GET",
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}