import { handleExtractTraits } from "../../../lib/server/extract-traits";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 120;
export const POST = (request: Request) => handleExtractTraits(request);
