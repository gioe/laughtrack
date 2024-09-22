
interface ProfilePageProps {
    id: string;
}

const ProfilePage: React.FC<ProfilePageProps> = async ({
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
        <ProfilePage id={params.id} />
    )
}