import { handlers } from "@/auth";
import { withRequestMetrics } from "@/lib/metrics";

export const GET = withRequestMetrics(handlers.GET);
export const POST = withRequestMetrics(handlers.POST);
