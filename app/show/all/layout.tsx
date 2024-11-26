import { FilterContextProvider } from "../../../contexts/FilterContext";
import { EntityType } from "../../../objects/enum";

export default function AllShowsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <FilterContextProvider type={EntityType.Show}>
            {children}
        </FilterContextProvider>
    );
}
