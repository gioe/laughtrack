'use client';

import { Select, SelectItem } from "@nextui-org/select";

interface DropdownItem {
    key: string;
    label: string
}

const items: DropdownItem[] = [
    { 
        key: "Popularity",
        label: "Pouplarity"
    },
    { 
        key: "Date",
        label: "Date"
    },
]

interface SearchResultsFiltersParams {
    cities: string[];
}

const SearchResultsFilters: React.FC<SearchResultsFiltersParams> = ({
    cities
}) => {

    return (

        <div className="flex w-full flex-wrap md:flex-nowrap gap-4">
            <Select
              labelPlacement={"outside"}
              label="Favorite Animal"
              placeholder="Select an animal"
              className="max-w-xs"
            >
              {items.map((animal) => (
                <SelectItem key={animal.key}>
                  {animal.label}
                </SelectItem>
              ))}
            </Select>
        </div>
    );


}

export default SearchResultsFilters;