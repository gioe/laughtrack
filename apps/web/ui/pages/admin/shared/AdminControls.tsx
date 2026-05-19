"use client";

import { Search } from "lucide-react";
import { Button } from "@/ui/components/ui/button";

export const ADMIN_PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 200];

export function clampAdminPage(page: number, totalPages: number) {
    return Math.min(Math.max(page, 1), Math.max(totalPages, 1));
}

export function AdminToolbar({ children }: { children: React.ReactNode }) {
    return (
        <div className="grid gap-3 rounded-md border border-copper/25 bg-white p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
            {children}
        </div>
    );
}

export function AdminSearchField({
    label,
    value,
    placeholder,
    onChange,
}: {
    label: string;
    value: string;
    placeholder: string;
    onChange: (value: string) => void;
}) {
    return (
        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
            {label}
            <span className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-soft-charcoal" />
                <input
                    type="search"
                    value={value}
                    onChange={(event) => onChange(event.target.value)}
                    className="w-full rounded-md border border-soft-charcoal/30 bg-white py-2 pl-10 pr-3 font-dmSans text-body text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                    placeholder={placeholder}
                />
            </span>
        </label>
    );
}

export function AdminSelectField<T extends string>({
    label,
    value,
    options,
    onChange,
}: {
    label: string;
    value: T;
    options: Array<{ value: T; label: string }>;
    onChange: (value: T) => void;
}) {
    return (
        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
            {label}
            <select
                value={value}
                onChange={(event) => onChange(event.target.value as T)}
                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
            >
                {options.map((option) => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>
        </label>
    );
}

export function AdminSegmentedControl<T extends string>({
    label,
    value,
    options,
    onChange,
}: {
    label: string;
    value: T;
    options: Array<{ value: T; label: string }>;
    onChange: (value: T) => void;
}) {
    return (
        <div>
            <div className="mb-1 font-dmSans text-body font-semibold text-cedar">
                {label}
            </div>
            <div
                className="inline-flex w-fit overflow-hidden rounded-md border border-soft-charcoal/30"
                aria-label={label}
            >
                {options.map((option, index) => (
                    <button
                        key={option.value}
                        type="button"
                        onClick={() => onChange(option.value)}
                        className={`px-3 py-2 font-dmSans text-body font-semibold ${
                            index > 0 ? "border-l border-soft-charcoal/30" : ""
                        } ${
                            value === option.value
                                ? "bg-copper-dark text-white"
                                : "bg-white text-cedar hover:bg-ecru-white"
                        }`}
                    >
                        {option.label}
                    </button>
                ))}
            </div>
        </div>
    );
}

export function AdminPagination({
    page,
    pageSize,
    totalItems,
    label,
    pageSizeOptions = ADMIN_PAGE_SIZE_OPTIONS,
    onPageChange,
    onPageSizeChange,
}: {
    page: number;
    pageSize: number;
    totalItems: number;
    label: string;
    pageSizeOptions?: number[];
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
}) {
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    const start = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
    const end = Math.min(page * pageSize, totalItems);

    return (
        <div className="flex flex-col gap-3 rounded-md border border-copper/25 bg-white px-3 py-2 font-dmSans text-body text-cedar md:flex-row md:items-center md:justify-between">
            <div className="font-semibold">
                {start}-{end} of {totalItems} {label}
            </div>
            <div className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-2 font-semibold">
                    Per page
                    <select
                        value={pageSize}
                        onChange={(event) =>
                            onPageSizeChange(Number(event.target.value))
                        }
                        className="rounded-md border border-soft-charcoal/30 bg-white px-2 py-1 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    >
                        {pageSizeOptions.map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </label>
                <Button
                    type="button"
                    variant="outline"
                    className="border-copper-dark bg-white text-copper-dark disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                    disabled={page <= 1}
                    onClick={() => onPageChange(page - 1)}
                >
                    Previous
                </Button>
                <span className="font-semibold">
                    Page {page} of {totalPages}
                </span>
                <Button
                    type="button"
                    variant="outline"
                    className="border-copper-dark bg-white text-copper-dark disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                    disabled={page >= totalPages}
                    onClick={() => onPageChange(page + 1)}
                >
                    Next
                </Button>
            </div>
        </div>
    );
}
