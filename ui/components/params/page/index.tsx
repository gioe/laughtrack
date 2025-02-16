"use client";

import { useState } from "react";
import { QueryProperty } from "@/objects/enum";
import TablePagination from "@mui/material/TablePagination";
import { useUrlParams } from "@/hooks/useUrlParams";

interface PageParamComponentProps {
    itemCount: number;
}

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    const { getParam, setParam } = useUrlParams();

    const defaultIndex = Number(getParam(QueryProperty.Page)) - 1;
    const defaultPageSize = Number(getParam(QueryProperty.Size));

    const [pageIndex, setPageIndex] = useState(defaultIndex);
    const [pageSize, setPageSize] = useState(defaultPageSize);

    const handleChangeOffset = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPageIndex: number,
    ) => {
        const newPageValue = newPageIndex + 1;
        setParam(QueryProperty.Page, newPageValue);
        setPageIndex(newPageIndex);
    };

    const handleChangeRows = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const rowSizeValue = parseInt(event.target.value, 8);
        setParam(QueryProperty.Size, rowSizeValue);
        setPageSize(rowSizeValue);
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
            count={itemCount}
            page={pageIndex}
            rowsPerPage={pageSize}
            onPageChange={handleChangeOffset}
            onRowsPerPageChange={handleChangeRows}
        />
    );
}
