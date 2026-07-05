'use client';

import { useMemo } from 'react';
import { AlertTriangle, Info, ShieldAlert, Flame, Droplets, Clock, Landmark, Biohazard, Shield, Radio, Building2, MapPin, Leaf } from 'lucide-react';
import profileTemplates from '@/lib/data/profile-templates.json';
import type { BuildingClass, ProjectType, WorkScopeItem, WorkScopeCategory, WorkScopeRiskDefinition } from '@/types/profiler';

interface RiskFlagsProps {
  buildingClass: BuildingClass | null;
  projectType: ProjectType | null;
  subclass: string[];
  scaleData: Record<string, number>;
  complexity: Record<string, string | string[]>;
  workScope?: string[];
}

interface RiskFlag {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  icon: React.ReactNode;
}

// Helper to find work scope item by value
function findWorkScopeItem(scopeValue: string, projectType: ProjectType | null): WorkScopeItem | null {
  if (!projectType) return null;
  const workScopeOptions = (profileTemplates as any).workScopeOptions;
  const typeConfig = workScopeOptions?.[projectType];
  if (!typeConfig) return null;

  for (const category of Object.values(typeConfig) as WorkScopeCategory[]) {
    const item = category.items.find((i: WorkScopeItem) => i.value === scopeValue);
    if (item) return item;
  }
  return null;
}

// Get risk icon based on risk flag key
function getRiskIcon(riskFlag: string): React.ReactNode {
  switch (riskFlag) {
    case 'combustible_cladding':
      return <Flame className="w-4 h-4" />;
    case 'asbestos':
    case 'pfas':
    case 'contaminated_land':
    case 'biosafety_3_plus':
      return <Biohazard className="w-4 h-4" />;
    case 'refrigerant_phase_out':
    case 'live_operations':
    case 'multi_jurisdictional':
      return <Info className="w-4 h-4" />;
    case 'high_security':
    case 'critical_infrastructure':
      return <Shield className="w-4 h-4" />;
    case 'remote_site':
      return <MapPin className="w-4 h-4" />;
    case 'gmp_manufacturing':
      return <Building2 className="w-4 h-4" />;
    case 'heritage_adaptive_reuse':
      return <Landmark className="w-4 h-4" />;
    case 'native_title':
      return <Leaf className="w-4 h-4" />;
    case 'flood_overlay':
      return <Droplets className="w-4 h-4" />;
    default:
      return <AlertTriangle className="w-4 h-4" />;
  }
}

export function RiskFlags({
  buildingClass,
  projectType,
  subclass,
  scaleData,
  complexity,
  workScope = [],
}: RiskFlagsProps) {
  const risks = useMemo<RiskFlag[]>(() => {
    const result: RiskFlag[] = [];

    if (!buildingClass || subclass.length === 0) return result;

    // Work scope-triggered risks
    const workScopeOptions = (profileTemplates as any).workScopeOptions;
    const riskDefinitions = workScopeOptions?.riskDefinitions || {};
    const addedRisks = new Set<string>();

    // Normalize site_conditions to array (supports both string and string[])
    const siteConditionsValue = complexity.site_conditions;
    const siteConditions: string[] = Array.isArray(siteConditionsValue)
      ? siteConditionsValue
      : siteConditionsValue ? [siteConditionsValue] : [];

    workScope.forEach((scopeValue) => {
      const scopeItem = findWorkScopeItem(scopeValue, projectType);
      if (scopeItem?.riskFlag && !addedRisks.has(scopeItem.riskFlag)) {
        addedRisks.add(scopeItem.riskFlag);
        const riskDef = riskDefinitions[scopeItem.riskFlag] as WorkScopeRiskDefinition | undefined;
        if (riskDef) {
          result.push({
            id: `scope-${scopeItem.riskFlag}`,
            severity: riskDef.severity,
            title: riskDef.title,
            description: riskDef.description,
            icon: getRiskIcon(scopeItem.riskFlag),
          });
        }
      }
    });

    // Bushfire + Class 9c warning (POWER-016)
    if (siteConditions.includes('bushfire') && subclass.includes('aged_care_9c')) {
      result.push({
        id: 'bushfire-9c',
        severity: 'critical',
        title: 'BAL-FZ + Class 9c Conflict',
        description: 'Bushfire Flame Zone (BAL-FZ) creates evacuation challenges for non-ambulatory residents. Consider alternate site or enhanced fire engineering.',
        icon: <Flame className="w-4 h-4" />,
      });
    }

    // Generic bushfire warning
    if (siteConditions.includes('bushfire')) {
      result.push({
        id: 'bushfire-general',
        severity: 'warning',
        title: 'Bushfire Attack Level',
        description: 'BAL ratings require compliant construction methods, materials certification, and may limit design options.',
        icon: <Flame className="w-4 h-4" />,
      });
    }

    // Flood overlay warning
    if (siteConditions.includes('flood')) {
      result.push({
        id: 'flood',
        severity: 'warning',
        title: 'Flood Overlay Zone',
        description: 'Flood planning controls may require elevated floor levels, flood-resistant materials, and stormwater management.',
        icon: <Droplets className="w-4 h-4" />,
      });
    }

    // Coastal site warning
    if (siteConditions.includes('coastal')) {
      result.push({
        id: 'coastal',
        severity: 'warning',
        title: 'Coastal Site',
        description: 'Coastal areas require consideration of sea level rise, storm surge, and corrosive marine environment on materials.',
        icon: <Droplets className="w-4 h-4" />,
      });
    }

    // Sloping site warning
    if (siteConditions.includes('sloping')) {
      result.push({
        id: 'sloping',
        severity: 'info',
        title: 'Sloping Site (>15%)',
        description: 'Steep gradients may require retaining walls, specialized foundations, and additional excavation/fill.',
        icon: <AlertTriangle className="w-4 h-4" />,
      });
    }

    // Heritage listed warning
    if (complexity.heritage === 'listed') {
      result.push({
        id: 'heritage',
        severity: 'warning',
        title: 'Heritage Listed Building',
        description: 'Heritage listing adds 15-40% to costs. Requires heritage consultant, conservation management plan, and extended approvals.',
        icon: <Landmark className="w-4 h-4" />,
      });
    }

    // State significant development timeline
    if (complexity.approval_pathway === 'state_significant') {
      result.push({
        id: 'state-sig',
        severity: 'warning',
        title: 'State Significant Development',
        description: 'SSD pathway typically adds 40+ weeks to approval timeline. Early engagement with planning authority recommended.',
        icon: <Clock className="w-4 h-4" />,
      });
    }

    // Hotel star rating vs rooms plausibility (POWER-005)
    if (subclass.includes('hotel')) {
      const rooms = scaleData.rooms || 0;
      const starRating = complexity.star_rating;

      if (starRating === 'luxury' && rooms > 200) {
        result.push({
          id: 'hotel-scale',
          severity: 'info',
          title: 'Large Luxury Hotel',
          description: 'Luxury hotels (5-star+) with 200+ rooms require significant amenity provision. Verify F&B, conference, and leisure scope.',
          icon: <Info className="w-4 h-4" />,
        });
      }

      if (starRating === '3_star' && rooms < 50) {
        result.push({
          id: 'hotel-viability',
          severity: 'info',
          title: 'Small Hotel Viability',
          description: '3-star hotels under 50 rooms may face operational viability challenges. Consider brand affiliation or upscaling.',
          icon: <Info className="w-4 h-4" />,
        });
      }
    }

    // Aged care beds vs viability (POWER-006)
    if (subclass.includes('aged_care_9c')) {
      const beds = scaleData.beds || 0;

      if (beds < 60) {
        result.push({
          id: 'aged-care-scale',
          severity: 'warning',
          title: 'Small Aged Care Facility',
          description: 'Facilities under 60 beds typically face viability challenges. Industry benchmark is 80-120 beds for operational efficiency.',
          icon: <AlertTriangle className="w-4 h-4" />,
        });
      }

      if (complexity.care_level === 'specialist_dementia' && (!scaleData.dementia_beds || scaleData.dementia_beds < beds * 0.3)) {
        result.push({
          id: 'dementia-ratio',
          severity: 'info',
          title: 'Dementia Bed Allocation',
          description: 'Specialist dementia care selected but dementia beds may be under-allocated. Consider increasing dedicated secure memory support beds.',
          icon: <Info className="w-4 h-4" />,
        });
      }
    }

    // Data centre tier implications
    if (subclass.includes('data_centre') && complexity.uptime_tier === 'tier_4') {
      result.push({
        id: 'dc-tier4',
        severity: 'info',
        title: 'Tier IV Data Centre',
        description: 'Tier IV (99.995% uptime) requires 2N+1 redundancy, significantly increasing mechanical/electrical costs and footprint.',
        icon: <ShieldAlert className="w-4 h-4" />,
      });
    }

    // Mixed-use transfer structure warning
    if (buildingClass === 'mixed' && complexity.transfer_structures === 'multiple') {
      result.push({
        id: 'transfer-struct',
        severity: 'warning',
        title: 'Multiple Transfer Structures',
        description: 'Multiple transfer levels add $500-2,000/m\u00b2 to structural costs. Early structural engineer engagement critical.',
        icon: <AlertTriangle className="w-4 h-4" />,
      });
    }

    // High-rise complexity
    const storeys = scaleData.storeys || scaleData.total_storeys || 0;
    if (storeys > 25) {
      result.push({
        id: 'high-rise',
        severity: 'info',
        title: 'High-Rise Construction',
        description: 'Buildings over 25 storeys require fire engineering, specialized construction methods, and longer programmes.',
        icon: <Info className="w-4 h-4" />,
      });
    }

    // High security classification risk (T122)
    if (complexity.security_classification === 'top_secret' || complexity.security_classification === 'sci') {
      const riskDef = riskDefinitions['high_security'] as WorkScopeRiskDefinition | undefined;
      if (riskDef && !addedRisks.has('high_security')) {
        addedRisks.add('high_security');
        result.push({
          id: 'high_security',
          severity: riskDef.severity,
          title: riskDef.title,
          description: riskDef.description,
          icon: getRiskIcon('high_security'),
        });
      }
    }

    // Remote site risk (T123)
    if (complexity.remoteness === 'very_remote') {
      const riskDef = riskDefinitions['remote_site'] as WorkScopeRiskDefinition | undefined;
      if (riskDef && !addedRisks.has('remote_site')) {
        addedRisks.add('remote_site');
        result.push({
          id: 'remote_site',
          severity: riskDef.severity,
          title: riskDef.title,
          description: riskDef.description,
          icon: getRiskIcon('remote_site'),
        });
      }
    }

    // Live operations risk (T124)
    if (complexity.operational_constraints === 'live_environment' || complexity.operational_constraints === '24_7_occupied') {
      const riskDef = riskDefinitions['live_operations'] as WorkScopeRiskDefinition | undefined;
      if (riskDef && !addedRisks.has('live_operations')) {
        addedRisks.add('live_operations');
        result.push({
          id: 'live_operations',
          severity: riskDef.severity,
          title: riskDef.title,
          description: riskDef.description,
          icon: getRiskIcon('live_operations'),
        });
      }
    }

    // Biosafety 3+ risk (T125)
    if (complexity.biosafety_level === 'bsl_3' || complexity.biosafety_level === 'bsl_4') {
      const riskDef = riskDefinitions['biosafety_3_plus'] as WorkScopeRiskDefinition | undefined;
      if (riskDef && !addedRisks.has('biosafety_3_plus')) {
        addedRisks.add('biosafety_3_plus');
        result.push({
          id: 'biosafety_3_plus',
          severity: riskDef.severity,
          title: riskDef.title,
          description: riskDef.description,
          icon: getRiskIcon('biosafety_3_plus'),
        });
      }
    }

    // Heritage adaptive reuse risk (T126)
    if (subclass.includes('heritage_conversion') || complexity.heritage === 'heritage_listed') {
      const riskDef = riskDefinitions['heritage_adaptive_reuse'] as WorkScopeRiskDefinition | undefined;
      if (riskDef && !addedRisks.has('heritage_adaptive_reuse')) {
        addedRisks.add('heritage_adaptive_reuse');
        result.push({
          id: 'heritage_adaptive_reuse',
          severity: riskDef.severity,
          title: riskDef.title,
          description: riskDef.description,
          icon: getRiskIcon('heritage_adaptive_reuse'),
        });
      }
    }

    return result;
  }, [buildingClass, projectType, subclass, scaleData, complexity, workScope]);

  if (risks.length === 0) return null;

  const severityStyles: Record<string, string> = {
    info: 'border-l-[var(--color-accent-teal)] bg-[var(--color-accent-teal)]/5',
    warning: 'border-l-amber-500 bg-amber-500/5',
    critical: 'border-l-red-500 bg-red-500/5',
  };

  const severityIconColors: Record<string, string> = {
    info: 'text-[var(--color-accent-teal)]',
    warning: 'text-amber-500',
    critical: 'text-red-500',
  };

  return (
    <div className="mt-4 space-y-2">
      <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
        <AlertTriangle className="w-3 h-3" />
        <span>Risk Flags ({risks.length})</span>
      </div>

      <div className="space-y-2">
        {risks.map((risk) => (
          <div
            key={risk.id}
            className={`p-3 rounded-r-lg border-l-2 ${severityStyles[risk.severity]}`}
          >
            <div className="flex items-start gap-2">
              <span className={severityIconColors[risk.severity]}>{risk.icon}</span>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-[var(--color-text-primary)]">
                  {risk.title}
                </h4>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {risk.description}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
