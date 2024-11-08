"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import TablePagination from "@mui/material/TablePagination";
import { URLParam } from "../../../../util/enum";
import { adjustUrlParams } from "../../../../util/primatives/paramUtil";
import { replaceRoute } from "../../../../util/navigationUtil";

interface PageParamComponentProps {
    itemCount: number;
}

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    const searchParams = useSearchParams();
    const currentPage = Number(searchParams.get("page")) || 0;

    const [page, setPage] = useState(currentPage);
    const [rowsPerPage, setRowsPerPage] = useState(10);

    const handleChangePage = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPage: number,
    ) => {
        const searchParams = new URLSearchParams();
        adjustUrlParams(searchParams, {
            value: newPage,
            key: URLParam.Page,
        });
        replaceRoute(searchParams);
        setPage(newPage);
    };

    const handleChangeRowsPerPage = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const searchParams = new URLSearchParams(useSearchParams());
        const rows = parseInt(event.target.value, 10);
        adjustUrlParams(searchParams, {
            value: rows,
            key: URLParam.Rows,
        });
        replaceRoute(searchParams);
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
