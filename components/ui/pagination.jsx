var __rest = (this && this.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
};
import * as React from "react";
import { ChevronLeftIcon, ChevronRightIcon, DotsHorizontalIcon, } from "@radix-ui/react-icons";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
const Pagination = (_a) => {
    var { className } = _a, props = __rest(_a, ["className"]);
    return (<nav role="navigation" aria-label="pagination" className={cn("mx-auto flex w-full justify-center", className)} {...props}/>);
};
Pagination.displayName = "Pagination";
const PaginationContent = React.forwardRef((_a, ref) => {
    var { className } = _a, props = __rest(_a, ["className"]);
    return (<ul ref={ref} className={cn("flex flex-row items-center gap-1", className)} {...props}/>);
});
PaginationContent.displayName = "PaginationContent";
const PaginationItem = React.forwardRef((_a, ref) => {
    var { className } = _a, props = __rest(_a, ["className"]);
    return (<li ref={ref} className={cn("", className)} {...props}/>);
});
PaginationItem.displayName = "PaginationItem";
const PaginationLink = (_a) => {
    var { className, isActive, size = "icon" } = _a, props = __rest(_a, ["className", "isActive", "size"]);
    return (<a aria-current={isActive ? "page" : undefined} className={cn(buttonVariants({
            variant: isActive ? "outline" : "ghost",
            size,
        }), className)} {...props}/>);
};
PaginationLink.displayName = "PaginationLink";
const PaginationPrevious = (_a) => {
    var { className } = _a, props = __rest(_a, ["className"]);
    return (<PaginationLink aria-label="Go to previous page" size="default" className={cn("gap-1 pl-2.5", className)} {...props}>
    <ChevronLeftIcon className="h-4 w-4"/>
    <span>Previous</span>
  </PaginationLink>);
};
PaginationPrevious.displayName = "PaginationPrevious";
const PaginationNext = (_a) => {
    var { className } = _a, props = __rest(_a, ["className"]);
    return (<PaginationLink aria-label="Go to next page" size="default" className={cn("gap-1 pr-2.5", className)} {...props}>
    <span>Next</span>
    <ChevronRightIcon className="h-4 w-4"/>
  </PaginationLink>);
};
PaginationNext.displayName = "PaginationNext";
const PaginationEllipsis = (_a) => {
    var { className } = _a, props = __rest(_a, ["className"]);
    return (<span aria-hidden className={cn("flex h-9 w-9 items-center justify-center", className)} {...props}>
    <DotsHorizontalIcon className="h-4 w-4"/>
    <span className="sr-only">More pages</span>
  </span>);
};
PaginationEllipsis.displayName = "PaginationEllipsis";
export { Pagination, PaginationContent, PaginationLink, PaginationItem, PaginationPrevious, PaginationNext, PaginationEllipsis, };
