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
    const paramsWrapper = ParamsWrapper.fromClientSideParams(
        usePathname(),
        new URLSearchParams(useSearchParams()),
    );
    const navigator = new Navigator(usePathname(), useRouter());

    const [page, setPage] = useState(
        paramsWrapper.getParamValue(URLParam.Page) as number,
    );

    const [rowsPerPage, setRowsPerPage] = useState(
        paramsWrapper.getParamValue(URLParam.Rows) as number,
    );

    const handleChangeOffset = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPage: number,
    ) => {
        paramsWrapper.setParamValue(URLParam.Page, newPage);
        navigator.replaceRoute(paramsWrapper.asParamsString());
        setPage(newPage);
    };

    const handleChangeRows = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const rowValue = parseInt(event.target.value, 10);
        paramsWrapper.setParamValue(URLParam.Rows, rowValue);
        navigator.replaceRoute(paramsWrapper.asParamsString());
        setRowsPerPage(rowValue);
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
            page={page}
            rowsPerPage={rowsPerPage}
            onPageChange={handleChangeOffset}
            onRowsPerPageChange={handleChangeRows}
        />
    );
}
