"use client";

import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { SearchParamsHelper } from "../../../objects/class/params/SearchParamsHelper";
import { Navigator } from "../../../objects/class/navigate/Navigator";
import { QueryProperty } from "../../../objects/enum/queryProperty";
import TablePagination from "@mui/material/TablePagination";

interface PageParamComponentProps {
    itemCount: number;
}

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

    const defaultIndex = Number(paramsHelper.getParamValue(QueryProperty.Page));
    const defaultPageSize = Number(
        paramsHelper.getParamValue(QueryProperty.Size),
    );

    const [pageIndex, setPageIndex] = useState(defaultIndex);
    const [pageSize, setPageSize] = useState(defaultPageSize);

    const handleChangeOffset = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPageIndex: number,
    ) => {
        setPageIndex(newPageIndex);

        const newPageValue = newPageIndex + 1;
        paramsHelper.setParamValue(QueryProperty.Page, newPageValue.toString());
        navigator.replaceRoute(paramsHelper.asParamsString());
    };

    const handleChangeRows = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const rowSizeValue = parseInt(event.target.value, 10);
        paramsHelper.setParamValue(QueryProperty.Size, rowSizeValue);
        navigator.replaceRoute(paramsHelper.asParamsString());
        setPageSize(rowSizeValue);
    };

    return (
        <TablePagination
            sx={{
                ".MuiTablePagination-displayedRows": {
                    color: "#C0C0C0",
                },
                ".MuiTablePagination-input": {
                    color: "#C0C0C0",
                },
                ".MuiTablePagination-selectLabel": {
                    color: "#C0C0C0",
                },
                ".MuiTablePagination-selectIcon": {
                    color: "#C0C0C0",
                },
                ".MuiTablePagination-actions": {
                    color: "#C0C0C0",
                },
                ".MuiButtonBase-root": {
                    color: "#C0C0C0",
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
