
interface ComedianDetailPageProps {
    id: string;
}

const ComedianDetailPage: React.FC<ComedianDetailPageProps> = async ({
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
        <ComedianDetailPage id={params.id} />
    )
}