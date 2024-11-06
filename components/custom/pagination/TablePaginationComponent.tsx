"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import TablePagination from "@mui/material/TablePagination";
import { handleUrlParams } from "../../../util/tailwindUtil";
import { URLParam } from "../../../util/enum";

interface TablePaginationComponentProps {
    itemCount: number;
}

export function TablePaginationComponent({
    itemCount,
}: Readonly<TablePaginationComponentProps>) {
    const searchParams = useSearchParams();
    const currentPage = Number(searchParams.get("page")) || 0;

    const [page, setPage] = useState(currentPage);
    const [rowsPerPage, setRowsPerPage] = useState(10);

    const handleChangePage = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPage: number,
    ) => {
        handleUrlParams(URLParam.Page, newPage);
        setPage(newPage);
    };

    const handleChangeRowsPerPage = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const rows = parseInt(event.target.value, 10);
        handleUrlParams(URLParam.Rows, rows);
        setRowsPerPage(rows);
        setPage(1);
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
            onPageChange={handleChangePage}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={handleChangeRowsPerPage}
        />
    );
}
