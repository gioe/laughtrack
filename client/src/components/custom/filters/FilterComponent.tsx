'use client';

import { capitalizeFirstLetter } from "@/lib/utils";
import { Select, SelectItem, SelectedItems } from "@nextui-org/select";
import { usePathname, useSearchParams } from "next/navigation";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Avatar, Chip } from "@nextui-org/react";

export type PropertyFilter = {
  key: string;
  label: string;
}

interface FilterComponentProps {
  selectedFilter?: string;
  propertyFilters?: PropertyFilter[];
  comedians?: any[]
  clubs?: any[]
}

const FilterComponent: React.FC<FilterComponentProps> = ({
  selectedFilter, 
  propertyFilters,
  comedians, 
  clubs
}) => {

  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter()

  const createNewPageUrl = (filter: number | string) => {
    const params = new URLSearchParams(searchParams);
    params.set("sort", filter.toString());
    const route = `${pathname}?${params.toString()}`;
    router.push(route)
  };

  const [value, setValue] = useState(capitalizeFirstLetter(selectedFilter) ?? 'date_time');

  const handleSelectionChange = (e: any) => {
    const filterValue = e.target.value as string
    setValue(filterValue);
    createNewPageUrl(filterValue.toLowerCase())
  };


  return (

    <div className="flex w-full flex-wrap md:flex-nowrap gap-4 ml-5">

      {
        propertyFilters && (
          <Select
          label="Sort By"
          className="max-w-xs text-silver-gray"
          selectedKeys={[value]}
          onChange={handleSelectionChange}
        >
          {propertyFilters.map((item) => (
            <SelectItem key={item.key}>
              {item.label}
            </SelectItem>
          ))}
        </Select>
        )
      }

      {comedians && (
        <Select
          items={comedians ?? []}
          variant="bordered"
          isMultiline={true}
          selectionMode="multiple"
          placeholder="Filter by comedian"
          labelPlacement="outside"
          className="max-w-xs text-silver-gray"
          classNames={{
            base: "max-w-xs",
            trigger: "min-h-12 py-2",
          }}
          renderValue={(items: SelectedItems<any>) => {
            return (
              <div className="flex flex-wrap gap-2">
                {items.map((item) => (
                  <Chip key={item.key}>{item.data?.name}</Chip>
                ))}
              </div>
            );
          }}
        >
          {(comedian) => (
            <SelectItem key={comedian.id} textValue={comedian.name}>
              <div className="flex gap-2 items-center">
                <Avatar alt={comedian.name} className="flex-shrink-0" size="sm" src={`/images/comedians/square/${comedian.name}.png`} />
                <div className="flex flex-col">
                  <span className="text-small">{comedian.name}</span>
                </div>
              </div>
            </SelectItem>
          )}
        </Select>
      )}

      {clubs && (
        <Select
          items={[]}
          variant="bordered"
          isMultiline={true}
          selectionMode="multiple"
          placeholder="Filter by club"
          labelPlacement="outside"
          className="max-w-xs text-silver-gray bg-white"
          classNames={{
            base: "max-w-xs",
            trigger: "min-h-12 py-2",
          }}
          renderValue={(items: SelectedItems<any>) => {
            return (
              <div className="flex flex-wrap gap-2">
                {items.map((item) => (
                  <Chip key={item.key}>{item.data?.name}</Chip>
                ))}
              </div>
            );
          }}
        >
          {(club) => (
            <SelectItem key={club.name} textValue={club.name}>
              <div className="flex gap-2 items-center">
                <Avatar alt={club.name} className="flex-shrink-0" size="sm" src={`/images/clubs/square/${club.name}.png`} />
                <div className="flex flex-col">
                  <span className="text-small">{club.name}</span>
                </div>
              </div>
            </SelectItem>
          )}
        </Select>
      )}

    </div>
  );


}

export default FilterComponent;