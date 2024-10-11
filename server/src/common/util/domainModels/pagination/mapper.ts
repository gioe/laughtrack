import { PaginationData } from "../../../models/interfaces/pagination.interface.js"


export const toPaginatedData = (input: any[], page: string, pageSize: string): PaginationData => {
    const currentPage = parseInt(page as string);
    const pageSizeInt = parseInt(pageSize as string);
    const startIndex = (currentPage - 1) * pageSizeInt;
    const endIndex = currentPage * pageSizeInt;
    const paginatedData = input.slice(startIndex, endIndex);
    const totalPages = Math.ceil(input.length / pageSizeInt);

    return {
        data: paginatedData,
        totalPages: isNaN(totalPages) ? 0 : totalPages
    }
}
