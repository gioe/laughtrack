
interface ClubDetailPageProps {
    id: string;
}

const ClubDetailPage: React.FC<ClubDetailPageProps> = async ({
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
        <ClubDetailPage id={params.id} />
    )
}