import { FullRoundedButton } from "../../../components/button/rounded/full";

export default async function Page(props: { params: Promise<{ id: string }> }) {
    const params = await props.params;
    return (
        <main className="flex-grow pt-24 bg-ivory">
            <FullRoundedButton label="Update" />
        </main>
    );
}
