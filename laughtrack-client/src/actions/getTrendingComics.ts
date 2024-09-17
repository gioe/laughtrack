import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getTrendingComics() {
    const trendingComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.TRENDING_COMEDIANS
    
    return fetch(trendingComediansUrl, {
        method: "POST",
      })
      .then((response) => response.json())
      .then((data) => {
        console.log(data)
        return data
      })
      .catch((error) => console.log(error))
}