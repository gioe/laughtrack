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

    return (
      <div>page</div>
    ) 
}

export default SearchPage;