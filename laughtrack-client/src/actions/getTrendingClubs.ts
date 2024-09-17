import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getTrendingClubs() {
    const trendingClubsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.TRENDING_CLUBS

    console.log(trendingClubsUrl)
    
    return fetch(trendingClubsUrl, {
      method: "GET",
    })
    .then((response) => response.json())
    .then((data) => data)
    .catch((error) => console.log(error))
}