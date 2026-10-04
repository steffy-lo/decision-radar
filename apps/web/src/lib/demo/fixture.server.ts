import "server-only";

import vendorDelay from "../../../../../fixtures/vendor-delay.json";
import vendorImpact from "../../../../../fixtures/vendor-delay-impact.json";
import { parseDemoFixture, parseImpactProjection } from "@/lib/domain/models";

/** One validated fixture for the route and future demo reset actions. */
export const demoFixture = parseDemoFixture(vendorDelay);
export const demoImpact = parseImpactProjection(vendorImpact, demoFixture.projectId, demoFixture.alerts[0].id);
