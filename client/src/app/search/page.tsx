import { notFound } from "next/navigation";

type Props = {
    searchParams: SearchParams
}

export type SearchParams = {
    url: URL;
    comics: any[]
    from: string;
    to: string;
}


function SearchPage({searchParams}: Props) {
    if (!searchParams.url) return notFound();

    const results = await fetchResults(searchParams)
    return (
      <div>page</div>
    ) 
}

export default SearchPage;