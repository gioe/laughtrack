import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getShowSearchResults(data: any) {

    console.log("GETTING SEARCH RESULTS")
    console.log(data)
    const trendingComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.SEARCH_SHOWS
    
    return fetch(trendingComediansUrl, {
        method: "POST",
        headers:{
            'Content-Type': 'application/x-www-form-urlencoded'
          },   
          body: new URLSearchParams({
            location: data.location,
            startDate: data.startDate,
            endDate: data.endDate
        }),
      })
      .then((response) => response.json())
      .then((data) => data)
      .catch((error) => console.log(error))
}