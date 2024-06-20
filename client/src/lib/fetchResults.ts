import { SearchParams } from '@/app/search/page'

export async function fetchResults(searchParams: SearchParams) {
    const url = new URL(searchParams.url)
    Object.keys(searchParams).forEach((key) => {
        if (key === "url" || key === "location") return

        const value = searchParams[key as keyof SearchParams];
        if (typeof value === 'string') {
            url.searchParams.append(key, value)
        }
    });

}