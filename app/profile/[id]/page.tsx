
interface ProfilePageProps {
    id: string;
}

const ProfilePage: React.FC<ProfilePageProps> = async () => {
    return (
        <div></div>
    )
}

export default async function Page(
    props: {
        params: Promise<{ id: string  }>
    }
) {
    const params = await props.params;
    return (
        <ProfilePage id={params.id} />
    )
}