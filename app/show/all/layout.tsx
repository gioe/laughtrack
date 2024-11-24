import { TagListProvider } from "../../../contexts/TagContext";

export default function AllShowsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <TagListProvider>{children}</TagListProvider>;
}
