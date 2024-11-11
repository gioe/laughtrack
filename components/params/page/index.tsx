"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import TablePagination from "@mui/material/TablePagination";
import { URLParam } from "../../../util/enum";
import { usePathname, useRouter } from "next/navigation";
import { LaughtrackSearchParams } from "../../../objects/classes/searchParams/LaughtrackSearchParams";

interface PageParamComponentProps {
    itemCount: number;
}

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    const params = LaughtrackSearchParams.asClientSideParams(
        new URLSearchParams(useSearchParams()),
        usePathname(),
        useRouter(),
    );
    const [page, setPage] = useState(
        params.getParamValue(URLParam.Page) as number,
    );

    const [rowsPerPage, setRowsPerPage] = useState(
        params.getParamValue(URLParam.Rows) as number,
    );

    console.log(
        `There are ${itemCount} results and you are currently on page ${page} with ${rowsPerPage} rows per page`,
    );

    const handleChangeOffset = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPage: number,
    ) => {
        params.setParamValue(URLParam.Page, newPage);
        params.replaceRoute();
        setPage(newPage);
    };

    const handleChangeRows = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const rowValue = parseInt(event.target.value, 10);
        params.setParamValue(URLParam.Rows, rowValue);
        params.replaceRoute();
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
