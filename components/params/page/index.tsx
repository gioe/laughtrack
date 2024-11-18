"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import TablePagination from "@mui/material/TablePagination";
import { URLParam } from "../../../objects/enum";
import { usePathname, useRouter } from "next/navigation";
import { ParamsWrapper } from "../../../objects/class/params/ParamsWrapper";
import { Navigator } from "../../../objects/class/navigate/Navigator";

interface PageParamComponentProps {
    itemCount: number;
}

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    ParamsWrapper.updateWithClientParams(useSearchParams());

    const navigator = new Navigator(usePathname(), useRouter());
    const defaultIndex =
        (ParamsWrapper.getParamValue(URLParam.Page) as number) - 1;
    const [pageIndex, setPageIndex] = useState(defaultIndex);

    const [rowsPerPage, setRowsPerPage] = useState(
        ParamsWrapper.getParamValue(URLParam.Size) as number,
    );

    const handleChangeOffset = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPageIndex: number,
    ) => {
        setPageIndex(newPageIndex);

        const newPageValue = newPageIndex + 1;
        ParamsWrapper.setParamValue(URLParam.Page, newPageValue);
        navigator.replaceRoute(ParamsWrapper.asParamsString());
    };

    const handleChangeRows = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const rowSizeValue = parseInt(event.target.value, 10);
        ParamsWrapper.setParamValue(URLParam.Size, rowSizeValue);
        navigator.replaceRoute(ParamsWrapper.asParamsString());
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
