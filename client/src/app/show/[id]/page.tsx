interface ShowDetailPageProps {
    id: string;
}

const ShowDetailPage: React.FC<ShowDetailPageProps> = async ({
    id,
}) => {
    return (
        <div></div>
    )
}

export default function Page({params}: {
    params: { id: string  }
}) { 
    return (
        <ShowDetailPage id={params.id} />
    )
}