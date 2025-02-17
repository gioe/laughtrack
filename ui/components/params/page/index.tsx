"use client";

import TablePagination from "@mui/material/TablePagination";
import { useState } from "react";
import { QueryProperty } from "@/objects/enum";
import { useUrlParams } from "@/hooks/useUrlParams";
import { buildPaginationData } from "@/util/pagination";

interface PageParamComponentProps {
    itemCount: number;
}

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    const { getTypedParam, setTypedParam } = useUrlParams();

    const index = getTypedParam(QueryProperty.Page);
    const pageSize = getTypedParam(QueryProperty.Size);

    // Initial state setup
    const initialState = buildPaginationData({
        index,
        pageSize,
        itemCount,
    });
    const [paginationData, setPaginationData] = useState(initialState);
    console.log(`The pagination data is ${JSON.stringify(paginationData)}`);
    const handleChangeOffset = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPageIndex: number,
    ) => {
        const newPageValue = newPageIndex + 1;
        setTypedParam(QueryProperty.Page, newPageValue);
        setPaginationData({
            ...paginationData,
            index: newPageIndex,
        });
    };

    const handleChangeRows = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const selectedSize = parseInt(event.target.value);
        setTypedParam(QueryProperty.Size, selectedSize);
        setPaginationData({
            ...paginationData,
            pageSize: selectedSize,
        });
    };

    return (
        <TablePagination
            sx={{
                ".MuiTablePagination-displayedRows": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiTablePagination-input": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiTablePagination-selectLabel": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiTablePagination-selectIcon": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiTablePagination-actions": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
                ".MuiButtonBase-root": {
                    color: "#B87333",
                    font: "dmSans",
                    fontSize: "16px",
                },
            }}
            component="div"
            count={paginationData.itemCount}
            page={paginationData.index}
            rowsPerPage={paginationData.pageSize}
            onPageChange={handleChangeOffset}
            onRowsPerPageChange={handleChangeRows}
        />
    );
}
