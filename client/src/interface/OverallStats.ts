import type { PropertyStats } from "./PropertyStats";
import type { RiskCounts } from "./RiskCounts";

export interface OverallStats {
    
    [property: string]: PropertyStats | undefined | { [property: string]: RiskCounts; } | any; // <- Change is here

    risk?: {
        [property: string]: RiskCounts;
    };
    
}
