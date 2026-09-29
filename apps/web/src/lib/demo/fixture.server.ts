import "server-only";

import vendorDelay from "../../../../../fixtures/vendor-delay.json";
import { parseDemoFixture } from "@/lib/domain/models";

/** One validated fixture for the route and future demo reset actions. */
export const demoFixture = parseDemoFixture(vendorDelay);
