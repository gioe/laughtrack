import { TagListProvider } from "../../../contexts/TagContext";
import { EntityType } from "../../../objects/enum";

export default function AllShowsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <TagListProvider type={EntityType.Show}>{children}</TagListProvider>;
}
