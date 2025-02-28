"use client";

import TablePagination from "@mui/material/TablePagination";
import { useEffect, useMemo } from "react";
import { QueryProperty } from "@/objects/enum";
import { useUrlParams } from "@/hooks/useUrlParams";

interface PageParamComponentProps {
    itemCount: number;
}

export function PageParamComponent({
    itemCount,
}: Readonly<PageParamComponentProps>) {
    const { getTypedParam, setTypedParam } = useUrlParams();

    const page = getTypedParam(QueryProperty.Page);
    const pageSize = getTypedParam(QueryProperty.Size);

    const correctedPage = useMemo(() => {
        const maxPage = Math.ceil(itemCount / pageSize);
        // The pagination library we're using is zero indexed by our pagination is not. We could our indexing but
        // zero indexing in the url may be weird for non-technical users.
        return Math.min(page, maxPage) - 1;
    }, [itemCount, page, pageSize]);

    // Update URL if we need to correct the page number
    useEffect(() => {
        if (correctedPage !== page - 1) {
            setTypedParam(QueryProperty.Page, correctedPage + 1);
        }
    }, [correctedPage, page, setTypedParam]);

    const handleChangeOffset = (
        event: React.MouseEvent<HTMLButtonElement> | null,
        newPageIndex: number,
    ) => {
        setTypedParam(QueryProperty.Page, newPageIndex + 1);
    };

    const handleChangeRows = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const selectedSize = parseInt(event.target.value);
        setTypedParam(QueryProperty.Size, selectedSize);
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
            page={correctedPage}
            rowsPerPage={pageSize}
            onPageChange={handleChangeOffset}
            onRowsPerPageChange={handleChangeRows}
        />
    );
}
