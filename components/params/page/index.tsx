"use client";

import { useState } from "react";
import TablePagination from "@mui/material/TablePagination";
import { URLParam } from "../../../objects/enum";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { SearchParamsHelper } from "../../../objects/class/params/SearchParamsHelper";
import { Navigator } from "../../../objects/class/navigate/Navigator";

interface PageParamComponentProps {
    itemCount: number;
}

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    const readOnlySearchParams = useSearchParams();
    const searchParams = new URLSearchParams(readOnlySearchParams);
    const paramsHelper = new SearchParamsHelper(searchParams);

    const navigator = new Navigator(usePathname(), useRouter());
    const defaultIndex =
        (paramsHelper.getParamValue(URLParam.Page) as number) - 1;
    const [pageIndex, setPageIndex] = useState(defaultIndex);

    const [rowsPerPage, setRowsPerPage] = useState(
        paramsHelper.getParamValue(URLParam.Size) as number,
    );

    const handleChangeOffset = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPageIndex: number,
    ) => {
        setPageIndex(newPageIndex);

        const newPageValue = newPageIndex + 1;
        paramsHelper.setParamValue(URLParam.Page, newPageValue);
        navigator.replaceRoute(paramsHelper.asParamsString());
    };

    const handleChangeRows = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const rowSizeValue = parseInt(event.target.value, 10);
        paramsHelper.setParamValue(URLParam.Size, rowSizeValue);
        navigator.replaceRoute(paramsHelper.asParamsString());
        setRowsPerPage(rowSizeValue);
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
            rowsPerPage={rowsPerPage}
            onPageChange={handleChangeOffset}
            onRowsPerPageChange={handleChangeRows}
        />
    );
}
