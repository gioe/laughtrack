"use client";

import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { usePageParams } from "./hooks/usePageParams";

interface PageParamComponentProps {
    itemCount: number;
}

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    const { currentPage, pageSize, updatePage, updatePageSize } =
        usePageParams(itemCount);

    const startItem = currentPage * pageSize + 1;
    const endItem = Math.min((currentPage + 1) * pageSize, itemCount);

    return (
        <div className="inline-flex items-center gap-4 text-copper text-sm">
            <div className="relative inline-flex items-center gap-2">
                <span className="whitespace-nowrap">Rows per page:</span>
                <div className="relative">
                    <select
                        value={pageSize}
                        onChange={(e) => updatePageSize(Number(e.target.value))}
                        className="appearance-none bg-copper/10 rounded-full pl-3 pr-8 py-1.5 
                                 text-copper cursor-pointer focus:outline-none focus:ring-1 
                                 focus:ring-copper hover:bg-copper/20 transition-colors"
                        style={{
                            WebkitAppearance: "none",
                            MozAppearance: "none",
                        }}
                    >
                        {PAGE_SIZE_OPTIONS.map((size) => (
                            <option
                                key={size}
                                value={size}
                                className="bg-white text-copper"
                            >
                                {size}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="inline-flex items-center whitespace-nowrap">
                {startItem}-{endItem} of {itemCount}
            </div>

            <div className="inline-flex items-center gap-1">
                <button
                    onClick={() => updatePage(currentPage - 1)}
                    disabled={currentPage === 0}
                    className="p-1.5 rounded-full hover:bg-copper/10 disabled:opacity-50 
                             disabled:hover:bg-transparent transition-colors duration-200 
                             focus:outline-none focus:ring-1 focus:ring-copper"
                    aria-label="Previous page"
                >
                    <ChevronLeft className="w-4 h-4" />
                </button>

                <button
                    onClick={() => updatePage(currentPage + 1)}
                    disabled={endItem >= itemCount}
                    className="p-1.5 rounded-full hover:bg-copper/10 disabled:opacity-50 
                             disabled:hover:bg-transparent transition-colors duration-200 
                             focus:outline-none focus:ring-1 focus:ring-copper"
                    aria-label="Next page"
                >
                    <ChevronRight className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}
