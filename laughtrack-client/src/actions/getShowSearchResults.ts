import { ComedianInterface } from "@/interfaces/comedian.interface"
import { PUBLIC_ROUTES } from "@/lib/routes"

export async function getShowSearchResults(data: any) {

    const trendingComediansUrl = "http://localhost:8080" + PUBLIC_ROUTES.SEARCH_SHOWS
    
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
      .then((data: ComedianInterface[]) => data)
      .catch((error) => console.log(error))
}