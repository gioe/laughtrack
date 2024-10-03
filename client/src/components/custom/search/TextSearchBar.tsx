'use client';
 
import {Input} from "@nextui-org/react";
import { useSearchParams, usePathname, useRouter } from 'next/navigation';
import SearchIcon from "../icons/SearchIcon";
import React, { useState } from "react";
import { useDebouncedCallback } from 'use-debounce';

interface SearchBarProps {
  query?: string
}

const TextSearchBar: React.FC<SearchBarProps> = ({
  query
}) => {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const { replace } = useRouter();

  const [value, setValue] = useState(query ?? "");

  const handleInputChange = (value: string) =>  {
    handleSearch(value)
    setValue(value)
  }

  const handleSearch = useDebouncedCallback((term) => {
    const params = new URLSearchParams(searchParams);
    if (term) {
        params.set('query', term);
      } else {
        params.delete('query');
      }
      replace(`${pathname}?${params.toString()}`);
  }, 300)
 
  return (
    <div className="w-full flex flex-col gap-2 max-w-[240px] m-5">
      <Input
        placeholder="Search for comedian"
        value={value}
        onValueChange={handleInputChange}
        startContent={
          <SearchIcon className="text-black/50 mb-0.5 dark:text-white/90 text-slate-400 pointer-events-none flex-shrink-0 mr-3" />
        }
      />
    </div>
  );
}

export default TextSearchBar;