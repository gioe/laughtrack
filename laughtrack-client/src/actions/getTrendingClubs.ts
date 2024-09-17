import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getTrendingClubs() {
    const trendingClubsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.TRENDING_CLUBS

    return fetch(trendingClubsUrl, {
      method: "POST",
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}