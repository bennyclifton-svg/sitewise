'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import profileTemplates from '@/lib/data/profile-templates.json';
import { useToast } from '@/lib/hooks/use-toast';
import { BuildingTabView, type BuildingTabTemplates } from '@/components/brief/BuildingTabView';
import type {
  BuildingClass,
  BuildingClassConfig,
  ComplexityOption,
  ProjectType,
  Region,
  ScaleField,
  WorkScopeCategory,
  WorkScopeClassOverride,
  WorkScopeItem,
  WorkScopeOptions,
} from '@/types/profiler';

type ProfileTemplateData = typeof profileTemplates & {
  workScopeOptions?: WorkScopeOptions;
};

const templates = profileTemplates as ProfileTemplateData;

const BUILDING_CLASS_ORDER: BuildingClass[] = [
  'residential',
  'commercial',
  'industrial',
  'institution',
  'mixed',
  'infrastructure',
  'agricultural',
  'defense_secure',
];

/**
 * Imperative profile controls exposed to a parent (e.g. BriefPanel's chrome
 * strip) so the Save / Load buttons can live outside this panel without
 * lifting all the form state up.
 */
export interface ProfilerControls {
  save: () => Promise<void>;
  load: () => Promise<void>;
  canSave: boolean;
}

interface ProfilerMiddlePanelProps {
  projectId: string;
  buildingClass: BuildingClass | null;
  projectType: ProjectType | null;
  onClassChange?: (cls: BuildingClass) => void;
  onTypeChange?: (type: ProjectType) => void;
  region?: Region;
  onRegionChange?: (region: Region) => void;
  initialData?: {
    subclass?: string[];
    subclassOther?: string[];
    scaleData?: Record<string, number>;
    complexity?: Record<string, string | string[]>;
    workScope?: string[];
  };
  onProfileComplete?: () => void;
  onProfileLoad?: (buildingClass: BuildingClass, projectType: ProjectType) => void;
  /**
   * Layout mode.
   * - 'fixed' (default): panel claims `h-full` and owns its own internal scroll
   *   via an inner `overflow-y-auto`. Use when this panel is the sole occupant
   *   of a fixed-height container.
   * - 'natural': panel renders at its natural content height with no internal
   *   scroll, allowing an outer wrapper to own the scroll context. Required
   *   when this panel is rendered alongside a `position: sticky` sibling
   *   (e.g. BriefPanel's Building tab) so the sticky element actually pins.
   */
  layout?: 'fixed' | 'natural';
  /**
   * Optional ref the panel populates with imperative profile controls. Lets
   * the parent's chrome render Save / Load buttons that delegate to this
   * panel's handlers without lifting form state up.
   */
  controlsRef?: React.MutableRefObject<ProfilerControls | null>;
}

interface ScopeCategoryWithItems {
  key: string;
  label: string;
  items: WorkScopeItem[];
}

function formatKey(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function arraysMatch(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

// Complexity dimensions that allow multiple values rather than a single value.
// site_conditions are not severity levels — they're independent characteristics
// (greenfield, sloping, bushfire, etc.) that can co-exist on one site.
const MULTI_SELECT_COMPLEXITY = new Set<string>(['site_conditions']);

// All Complexity dimensions share the same accent — keeps the card calm and
// reinforces that complexity is one composite axis. Peach/orange chosen to
// echo the AggregateSlider thumb colour above the chips.
const COMPLEXITY_ACCENT = 'var(--sw-peach)';
function dimensionAccent(_key: string): string {
  return COMPLEXITY_ACCENT;
}

// Short labels for the Complexity card's left column. Falls back to formatKey().
const DIMENSION_LABEL: Record<string, string> = {
  quality_tier: 'Quality',
  site_conditions: 'Site',
  contamination_level: 'Contamination',
  access_constraints: 'Access',
  operational_constraints: 'Operational',
  procurement_route: 'Procurement',
  stakeholder_complexity: 'Stakeholder',
  environmental_sensitivity: 'Environmental',
};
function dimensionLabel(key: string): string {
  return DIMENSION_LABEL[key] ?? formatKey(key);
}

// ---- Project type labels ----
const PROJECT_TYPE_OPTIONS: Array<{ value: ProjectType; label: string }> =
  (profileTemplates.projectTypes as Array<{ value: string; label: string }>).map(
    (t) => ({ value: t.value as ProjectType, label: t.label }),
  );

// ---- Building class labels in canonical order ----
const BUILDING_CLASS_OPTIONS: Array<{ value: BuildingClass; label: string }> =
  BUILDING_CLASS_ORDER.map((key) => ({
    value: key,
    label:
      (profileTemplates.buildingClasses as Record<string, BuildingClassConfig>)[key]
        ?.label ?? formatKey(key),
  }));

// ---- Derivation helpers (NCC, cost band, complexity band, contingency) ----

function deriveComplexityBand(score: number | null | undefined): string | null {
  if (score == null) return null;
  if (score < 3) return 'low';
  if (score < 6) return 'standard';
  if (score < 8) return 'high';
  if (score < 10) return 'very high';
  return 'extreme';
}

// ---- RiskFlags translation: replicates the existing RiskFlags logic, but
// returns the wireframe shape `{ label, description, tag }`. ----

interface InlineRiskFlag {
  label: string;
  description: string;
  tag: string;
}

function findWorkScopeItem(
  scopeValue: string,
  projectType: ProjectType | null,
): WorkScopeItem | null {
  if (!projectType) return null;
  const workScopeOptions = templates.workScopeOptions;
  const typeConfig =
    (workScopeOptions as unknown as Record<string, Record<string, WorkScopeCategory>>)?.[
      projectType
    ];
  if (!typeConfig) return null;
  for (const category of Object.values(typeConfig) as WorkScopeCategory[]) {
    const item = category.items.find((i) => i.value === scopeValue);
    if (item) return item;
  }
  return null;
}

function deriveRiskFlags(args: {
  buildingClass: BuildingClass | null;
  projectType: ProjectType | null;
  subclass: string[];
  scaleData: Record<string, number>;
  complexity: Record<string, string | string[]>;
  workScope: string[];
}): InlineRiskFlag[] {
  const { buildingClass, projectType, subclass, scaleData, complexity, workScope } = args;
  const result: InlineRiskFlag[] = [];
  if (!buildingClass || subclass.length === 0) return result;

  const workScopeOptions = templates.workScopeOptions;
  const riskDefinitions =
    (workScopeOptions as unknown as { riskDefinitions?: Record<string, { severity: string; title: string; description: string }> })
      ?.riskDefinitions ?? {};
  const seen = new Set<string>();

  const siteConditionsValue = complexity.site_conditions;
  const siteConditions: string[] = Array.isArray(siteConditionsValue)
    ? siteConditionsValue
    : siteConditionsValue
      ? [siteConditionsValue as string]
      : [];

  workScope.forEach((scopeValue) => {
    const item = findWorkScopeItem(scopeValue, projectType);
    if (item?.riskFlag && !seen.has(item.riskFlag)) {
      const def = riskDefinitions[item.riskFlag];
      if (def) {
        seen.add(item.riskFlag);
        result.push({
          label: def.title,
          description: def.description,
          tag: def.severity.toUpperCase(),
        });
      }
    }
  });

  if (siteConditions.includes('bushfire') && subclass.includes('aged_care_9c')) {
    result.push({
      label: 'BAL-FZ + Class 9c Conflict',
      description:
        'Bushfire Flame Zone (BAL-FZ) creates evacuation challenges for non-ambulatory residents. Consider alternate site or enhanced fire engineering.',
      tag: 'CRITICAL',
    });
  }
  if (siteConditions.includes('bushfire')) {
    result.push({
      label: 'Bushfire Attack Level',
      description:
        'BAL ratings require compliant construction methods, materials certification, and may limit design options.',
      tag: 'WARNING',
    });
  }
  if (siteConditions.includes('flood')) {
    result.push({
      label: 'Flood Overlay Zone',
      description:
        'Flood planning controls may require elevated floor levels, flood-resistant materials, and stormwater management.',
      tag: 'WARNING',
    });
  }
  if (siteConditions.includes('coastal')) {
    result.push({
      label: 'Coastal Site',
      description:
        'Coastal areas require consideration of sea level rise, storm surge, and corrosive marine environment on materials.',
      tag: 'WARNING',
    });
  }
  if (siteConditions.includes('sloping')) {
    result.push({
      label: 'Sloping Site (>15%)',
      description:
        'Steep gradients may require retaining walls, specialized foundations, and additional excavation/fill.',
      tag: 'INFO',
    });
  }
  if (complexity.heritage === 'listed') {
    result.push({
      label: 'Heritage Listed Building',
      description:
        'Heritage listing adds 15-40% to costs. Requires heritage consultant, conservation management plan, and extended approvals.',
      tag: 'WARNING',
    });
  }
  if (complexity.approval_pathway === 'state_significant') {
    result.push({
      label: 'State Significant Development',
      description:
        'SSD pathway typically adds 40+ weeks to approval timeline. Early engagement with planning authority recommended.',
      tag: 'WARNING',
    });
  }
  const storeys = (scaleData.storeys || scaleData.total_storeys || 0) as number;
  if (storeys > 25) {
    result.push({
      label: 'High-Rise Construction',
      description:
        'Buildings over 25 storeys require fire engineering, specialized construction methods, and longer programmes.',
      tag: 'INFO',
    });
  }
  return result;
}

// ---- Disciplines translation: replicates ConsultantPreview logic, returns
// `{ required, suggested }` arrays of discipline names. ----

const BASE_DISCIPLINES = [
  'Architect',
  'Structural',
  'Civil',
  'Mechanical',
  'Electrical',
  'Hydraulic',
];

const CLASS_DISCIPLINES: Record<string, string[]> = {
  residential: ['Landscape', 'Acoustic'],
  commercial: ['Facade', 'Acoustic', 'ESD'],
  industrial: ['Fire Engineer', 'ESD'],
  institution: ['Acoustic', 'Security'],
  mixed: ['Facade', 'Traffic', 'Acoustic'],
  infrastructure: ['Geotech', 'Environmental', 'Traffic'],
  defense_secure: ['Security', 'SCIF Specialist', 'Fire Engineer'],
  agricultural: ['Agricultural', 'Environmental', 'Civil'],
};

const SUBCLASS_DISCIPLINES: Record<string, string[]> = {
  aged_care_9c: ['Fire Engineer', 'Access', 'Kitchen Consultant'],
  healthcare_hospital: [
    'Medical Planner',
    'Fire Engineer',
    'Acoustic',
    'Infection Control Consultant',
  ],
  data_centre: ['Data Centre Specialist', 'Fire Engineer', 'Security'],
  hotel: ['Interior', 'Kitchen Consultant', 'Acoustic', 'Lighting'],
};

const COMPLEXITY_DISCIPLINES: Record<string, string> = {
  heritage: 'Heritage',
  listed: 'Heritage Architect',
  bushfire: 'Bushfire',
  flood: 'Flood',
  state_significant: 'Planning',
  complex_da: 'Town Planning',
  triple_cert: 'ESD',
  net_zero: 'Net Zero Consultant',
  tier_3: 'Commissioning Agent',
  tier_4: 'Commissioning Agent',
};

function deriveDisciplines(args: {
  buildingClass: BuildingClass | null;
  subclass: string[];
  complexity: Record<string, string | string[]>;
  workScope: string[];
  projectType: ProjectType | null;
}): string[] {
  const { buildingClass, subclass, complexity, workScope, projectType } = args;
  if (!buildingClass || subclass.length === 0) return [];
  const names = new Set<string>();
  BASE_DISCIPLINES.forEach((name) => names.add(name));
  (CLASS_DISCIPLINES[buildingClass] ?? []).forEach((name) => names.add(name));
  subclass.forEach((sub) => {
    (SUBCLASS_DISCIPLINES[sub] ?? []).forEach((name) => names.add(name));
  });
  Object.values(complexity).forEach((value) => {
    const values = Array.isArray(value) ? value : [value];
    values.forEach((v) => {
      const hit = COMPLEXITY_DISCIPLINES[v as string];
      if (hit) names.add(hit);
    });
  });
  workScope.forEach((scopeValue) => {
    const item = findWorkScopeItem(scopeValue, projectType);
    item?.consultants?.forEach((c) => names.add(c));
  });
  return Array.from(names).sort((a, b) => a.localeCompare(b));
}

// ============================================================================
// COMPONENT
// ============================================================================

export function ProfilerMiddlePanel({
  projectId,
  buildingClass,
  projectType,
  onClassChange,
  onTypeChange,
  initialData,
  onProfileComplete,
  onProfileLoad,
  layout = 'fixed',
  controlsRef,
}: ProfilerMiddlePanelProps) {
  const { toast } = useToast();
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSubclasses, setSelectedSubclasses] = useState<string[]>(initialData?.subclass || []);
  const [subclassOther, setSubclassOther] = useState<string[]>(initialData?.subclassOther || []);
  const [scaleData, setScaleData] = useState<Record<string, number>>(initialData?.scaleData || {});
  const [complexity, setComplexity] = useState<Record<string, string | string[]>>(initialData?.complexity || {});
  const [workScope, setWorkScope] = useState<string[]>(initialData?.workScope || []);
  // Slider levels: kept in their original 0-N domain to preserve existing
  // bucketing logic (`buildComplexityFromLevel`, `buildScopeFromLevel`).
  const [complexityLevel, setComplexityLevel] = useState(2);
  const [complexityOverrides, setComplexityOverrides] = useState<Record<string, string>>({});
  const [scopeLevel, setScopeLevel] = useState(0);
  const [scopeOverrides, setScopeOverrides] = useState<Record<string, string[]>>({});
  // Composite complexity score from API (set on Save / Load).
  const [complexityScore, setComplexityScore] = useState<number | null>(null);
  const prevBuildingClassRef = useRef<BuildingClass | null>(buildingClass);

  useEffect(() => {
    const prevClass = prevBuildingClassRef.current;
    if (prevClass !== null && buildingClass !== null && prevClass !== buildingClass && !initialData && !isLoading && !isSaving) {
      setSelectedSubclasses([]);
      setSubclassOther([]);
      setScaleData({});
      setComplexity({});
      setComplexityOverrides({});
      setWorkScope([]);
      setScopeOverrides({});
      setScopeLevel(0);
    }
    prevBuildingClassRef.current = buildingClass;
  }, [buildingClass, initialData, isLoading, isSaving]);

  useEffect(() => {
    if (initialData) {
      setSelectedSubclasses(initialData.subclass || []);
      setSubclassOther(initialData.subclassOther || []);
      setScaleData(initialData.scaleData || {});
      setComplexity(initialData.complexity || {});
      setComplexityOverrides({});
      setWorkScope(initialData.workScope || []);
      setScopeOverrides({});
      setScopeLevel((initialData.workScope?.length || 0) > 0 ? 2 : 0);
    }
  }, [initialData]);

  const classConfig = useMemo<BuildingClassConfig | null>(() => {
    if (!buildingClass) return null;
    return (profileTemplates.buildingClasses as Record<string, BuildingClassConfig>)[buildingClass] ?? null;
  }, [buildingClass]);

  const scaleFields = useMemo<ScaleField[]>(() => {
    if (!classConfig) return [];
    const primarySubclass = selectedSubclasses[0];
    if (primarySubclass && classConfig.scaleFields[primarySubclass]) {
      return classConfig.scaleFields[primarySubclass];
    }
    return classConfig.scaleFields.default;
  }, [classConfig, selectedSubclasses]);

  const complexityOptions = useMemo<Record<string, ComplexityOption[]>>(() => {
    if (!classConfig) return {};
    const primarySubclass = selectedSubclasses[0];
    let options = classConfig.complexityOptions.default;
    if (primarySubclass && classConfig.complexityOptions[primarySubclass]) {
      options = classConfig.complexityOptions[primarySubclass];
    }
    if (Array.isArray(options)) return { default: options };
    return options as Record<string, ComplexityOption[]>;
  }, [classConfig, selectedSubclasses]);

  const scopeCategories = useMemo<ScopeCategoryWithItems[]>(() => {
    if (!buildingClass || !projectType) return [];
    const workScopeOptions = templates.workScopeOptions;
    if (!workScopeOptions) return [];

    const applicableTypes = (workScopeOptions.applicableProjectTypes as string[]) ?? [];
    if (!applicableTypes.includes(projectType)) return [];

    const typeConfig = workScopeOptions[projectType] as Record<string, WorkScopeCategory> | undefined;
    if (!typeConfig) return [];

    const categories = Object.entries(typeConfig).map(([key, category]) => ({
      key,
      label: category.label,
      items: [...category.items],
    }));

    const classOverrides = (workScopeOptions.classOverrides as Record<string, { additionalItems?: WorkScopeClassOverride[] }> | undefined)?.[buildingClass];
    classOverrides?.additionalItems?.forEach((override) => {
      const [overrideType, categoryKey] = override.category.split('.');
      if (overrideType !== projectType) return;
      const category = categories.find((item) => item.key === categoryKey);
      if (!category) return;
      category.items.push({
        value: override.value,
        label: override.label,
        consultants: override.consultants,
      });
    });

    return categories;
  }, [buildingClass, projectType]);

  // ---- Handlers (state-mutating logic preserved verbatim) ----

  const handleSubclassToggle = (subclass: string) => {
    const maxSubclasses = buildingClass === 'mixed' ? 4 : 1;

    setSelectedSubclasses((prev) => {
      if (prev.includes(subclass)) return prev.filter((item) => item !== subclass);
      if (prev.length >= maxSubclasses) return maxSubclasses === 1 ? [subclass] : [...prev.slice(1), subclass];
      return [...prev, subclass];
    });

    setScaleData({});
    setComplexity({});
    setComplexityOverrides({});
  };

  const selectType = (type: ProjectType) => {
    onTypeChange?.(type);
    setWorkScope([]);
    setScopeOverrides({});
    setScopeLevel(0);
  };

  const buildComplexityFromLevel = useCallback((level: number, overrides: Record<string, string>) => {
    if (level <= 0) return {};

    return Object.entries(complexityOptions).reduce<Record<string, string>>((next, [dimension, options]) => {
      if (options.length === 0) return next;
      // Multi-select dimensions are user-driven — slider does not auto-fill them.
      if (MULTI_SELECT_COMPLEXITY.has(dimension)) return next;
      const defaultIndex = Math.min(level - 1, options.length - 1);
      const override = overrides[dimension];
      next[dimension] = override && options.some((option) => option.value === override)
        ? override
        : options[defaultIndex].value;
      return next;
    }, {});
  }, [complexityOptions]);

  const applyComplexityLevel = useCallback((level: number) => {
    setComplexityLevel(level);
    if (level <= 0) {
      setComplexityOverrides({});
    }
    setComplexity((prev) => {
      // Preserve user-driven multi-select selections across slider changes.
      const preserved: Record<string, string | string[]> = {};
      MULTI_SELECT_COMPLEXITY.forEach((dim) => {
        if (prev[dim] !== undefined) preserved[dim] = prev[dim];
      });
      if (level <= 0) return preserved;
      return { ...buildComplexityFromLevel(level, complexityOverrides), ...preserved };
    });
  }, [buildComplexityFromLevel, complexityOverrides]);

  const selectComplexityOption = (dimension: string, option: ComplexityOption) => {
    if (MULTI_SELECT_COMPLEXITY.has(dimension)) {
      setComplexity((prev) => {
        const current = prev[dimension];
        const currentArray = Array.isArray(current)
          ? current
          : current
            ? [current as string]
            : [];
        const next = currentArray.includes(option.value)
          ? currentArray.filter((v) => v !== option.value)
          : [...currentArray, option.value];
        const nextState = { ...prev };
        if (next.length === 0) delete nextState[dimension];
        else nextState[dimension] = next;
        return nextState;
      });
      return;
    }

    const options = complexityOptions[dimension] ?? [];
    const defaultIndex = complexityLevel > 0
      ? Math.min(complexityLevel - 1, Math.max(options.length - 1, 0))
      : -1;
    const defaultValue = defaultIndex >= 0 ? options[defaultIndex]?.value : undefined;
    const rawValue = complexity[dimension];
    const isSelected = Array.isArray(rawValue)
      ? rawValue.includes(option.value)
      : rawValue === option.value;

    if (isSelected && defaultValue === undefined) {
      setComplexityOverrides((prev) => {
        const next = { ...prev };
        delete next[dimension];
        return next;
      });
      setComplexity((prev) => {
        const next = { ...prev };
        delete next[dimension];
        return next;
      });
      return;
    }

    if (isSelected && option.value !== defaultValue) {
      setComplexityOverrides((prev) => {
        const next = { ...prev };
        delete next[dimension];
        return next;
      });
      setComplexity((prev) => ({ ...prev, [dimension]: defaultValue as string }));
      return;
    }

    setComplexityOverrides((prev) => {
      const next = { ...prev };
      if (option.value === defaultValue) delete next[dimension];
      else next[dimension] = option.value;
      return next;
    });
    setComplexity((prev) => ({ ...prev, [dimension]: option.value }));
  };

  const defaultScopeCount = useCallback((items: WorkScopeItem[], level = scopeLevel) => {
    if (items.length === 0 || level <= 0) return 0;
    if (level >= 3) return items.length;
    return Math.ceil((level / 3) * items.length);
  }, [scopeLevel]);

  const defaultScopeValues = useCallback((items: WorkScopeItem[], level = scopeLevel) => {
    return items.slice(0, defaultScopeCount(items, level)).map((item) => item.value);
  }, [defaultScopeCount, scopeLevel]);

  const buildScopeFromLevel = useCallback((level: number, overrides: Record<string, string[]>) => {
    if (level <= 0) return [];

    return scopeCategories.flatMap((category) => {
      return overrides[category.key] ?? defaultScopeValues(category.items, level);
    });
  }, [defaultScopeValues, scopeCategories]);

  const applyScopeLevel = (level: number) => {
    setScopeLevel(level);
    if (level <= 0) {
      setScopeOverrides({});
      setWorkScope([]);
      return;
    }
    setWorkScope(buildScopeFromLevel(level, scopeOverrides));
  };

  /**
   * Handles a click on any scope chip — finds the owning category, then applies
   * the original `selectScopeItem` semantics (overrides + workScope mutation).
   * Adapter shape so BuildingTabView only needs the value, not the category.
   */
  const handleScopeToggle = (scopeValue: string) => {
    const category = scopeCategories.find((cat) =>
      cat.items.some((item) => item.value === scopeValue),
    );
    if (!category) return;
    const item = category.items.find((i) => i.value === scopeValue);
    if (!item) return;

    const defaultValues = defaultScopeValues(category.items);
    const categoryValues = category.items.map((scopeItem) => scopeItem.value);
    const currentValues = category.items
      .map((scopeItem) => scopeItem.value)
      .filter((value) => workScope.includes(value));
    const valueSet = new Set(currentValues);
    if (valueSet.has(item.value)) valueSet.delete(item.value);
    else valueSet.add(item.value);

    const selectedValues = category.items
      .map((scopeItem) => scopeItem.value)
      .filter((value) => valueSet.has(value));
    const nextOverrides = { ...scopeOverrides };
    if (arraysMatch(selectedValues, defaultValues)) delete nextOverrides[category.key];
    else nextOverrides[category.key] = selectedValues;
    setScopeOverrides(nextOverrides);
    setWorkScope([
      ...workScope.filter((value) => !categoryValues.includes(value)),
      ...selectedValues,
    ]);
  };

  /**
   * Adapter for BuildingTabView's complexity chip click — resolves the option
   * object from the (dimension, value) pair and delegates to the existing
   * single/multi-select handler.
   */
  const handleComplexityChange = (dimension: string, value: string) => {
    const options = complexityOptions[dimension] ?? [];
    const option = options.find((o) => o.value === value);
    if (!option) return;
    selectComplexityOption(dimension, option);
  };

  // BuildingTabView's slider uses 0-100. Existing complexityLevel is 0-4
  // (5 buckets) and scopeLevel is 0-3 (4 buckets). Scale on the way in/out.
  const COMPLEXITY_BUCKETS = 4; // levels 0..4
  const SCOPE_BUCKETS = 3; // levels 0..3

  const complexitySliderValue = Math.round((complexityLevel / COMPLEXITY_BUCKETS) * 100);
  const scopeSliderValue = Math.round((scopeLevel / SCOPE_BUCKETS) * 100);

  const handleComplexitySliderChange = (sliderValue: number) => {
    const level = Math.round((sliderValue / 100) * COMPLEXITY_BUCKETS);
    applyComplexityLevel(level);
  };
  const handleScopeSliderChange = (sliderValue: number) => {
    const level = Math.round((sliderValue / 100) * SCOPE_BUCKETS);
    applyScopeLevel(level);
  };

  // ---- Persistence (verbatim) ----

  const handleSave = async () => {
    if (!buildingClass || !projectType) {
      toast({
        title: 'Missing Required Fields',
        description: 'Please select building class and project type',
        variant: 'destructive',
      });
      return;
    }

    setIsSaving(true);
    try {
      const payload = {
        buildingClass,
        projectType,
        subclass: selectedSubclasses,
        subclassOther: subclassOther.length > 0 ? subclassOther : null,
        scaleData,
        complexity,
        workScope: workScope.length > 0 ? workScope : null,
      };

      const response = await fetch(`/api/projects/${projectId}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error?.message || 'Failed to save profile');
      }

      const result = await response.json().catch(() => null);
      if (result?.data?.complexityScore != null) {
        setComplexityScore(Number(result.data.complexityScore));
      }

      toast({
        title: 'Profile Saved',
        description: 'Project profile has been updated',
        variant: 'success',
      });
      onProfileComplete?.();
    } catch (error) {
      toast({
        title: 'Save Failed',
        description: error instanceof Error ? error.message : 'Failed to save profile',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleLoad = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/projects/${projectId}/profile`);
      if (!response.ok) throw new Error('Failed to load profile');
      const result = await response.json();
      const data = result.data;
      if (!data) throw new Error('No saved profile found');

      const loadedSubclasses = data.subclass ?? [];
      const loadedSubclassOther = data.subclassOther ?? [];
      const loadedScaleData = data.scaleData ?? {};
      const loadedComplexity = data.complexity ?? {};
      const loadedWorkScope = data.workScope ?? [];

      setSelectedSubclasses(loadedSubclasses);
      setSubclassOther(loadedSubclassOther);
      setScaleData(loadedScaleData);
      setComplexity(loadedComplexity);
      setComplexityOverrides({});
      setWorkScope(loadedWorkScope);
      setScopeOverrides({});
      setScopeLevel(loadedWorkScope.length > 0 ? 2 : 0);
      if (data.complexityScore != null) {
        setComplexityScore(Number(data.complexityScore));
      }

      if (data.buildingClass && data.projectType) {
        onProfileLoad?.(data.buildingClass as BuildingClass, data.projectType as ProjectType);
      }

      toast({
        title: 'Profile Loaded',
        description: 'Previously saved profile has been restored',
        variant: 'success',
      });
    } catch (error) {
      toast({
        title: 'Load Failed',
        description: error instanceof Error ? error.message : 'No saved profile found',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const canSave = Boolean(buildingClass && projectType);

  // Expose imperative save/load to parents via the optional controls ref.
  // Refs are mutable and don't trigger re-renders; assigning during render
  // keeps the parent's handle in sync with the latest closure each render.
  if (controlsRef) {
    controlsRef.current = { save: handleSave, load: handleLoad, canSave };
  }

  // ---- Derive BuildingTabTemplates (the BuildingTabView contract) ----

  const derivedTemplates = useMemo<BuildingTabTemplates>(() => {
    const subclassOptions = classConfig?.subclasses
      ? classConfig.subclasses.map((s) => ({ value: s.value, label: s.label }))
      : [];

    const complexityDimensions = Object.entries(complexityOptions).map(
      ([key, options]) => ({
        key,
        label: dimensionLabel(key),
        options,
        accent: dimensionAccent(key),
      }),
    );

    const scopeGroups = scopeCategories.map((cat) => ({
      categoryLabel: cat.label,
      items: cat.items,
    }));

    const scaleFieldsView = scaleFields.map((f) => ({
      key: f.key,
      label: f.label,
      unit: f.unit,
      note: f.note,
      noteAccent: f.noteAccent,
      type: f.type,
      min: f.min,
      max: f.max,
      placeholder: f.placeholder,
      parts: f.parts,
      partsSeparator: f.partsSeparator,
      partsLabel: f.partsLabel,
    }));

    return {
      buildingClasses: BUILDING_CLASS_OPTIONS,
      projectTypes: PROJECT_TYPE_OPTIONS,
      subclassOptions,
      complexityDimensions,
      scopeGroups,
      scaleFields: scaleFieldsView,
    };
  }, [classConfig, complexityOptions, scopeCategories, scaleFields]);

  // ---- Derive optional extras ----

  const complexityBand = useMemo(
    () => deriveComplexityBand(complexityScore),
    [complexityScore],
  );
  const riskFlags = useMemo(
    () =>
      deriveRiskFlags({
        buildingClass,
        projectType,
        subclass: selectedSubclasses,
        scaleData,
        complexity,
        workScope,
      }),
    [buildingClass, projectType, selectedSubclasses, scaleData, complexity, workScope],
  );
  const disciplines = useMemo(
    () =>
      deriveDisciplines({
        buildingClass,
        subclass: selectedSubclasses,
        complexity,
        workScope,
        projectType,
      }),
    [buildingClass, selectedSubclasses, complexity, workScope, projectType],
  );

  // In 'natural' layout, this panel renders at its content height with no
  // internal scroll so the parent's outer wrapper can own the scroll context
  // (required for `position: sticky` siblings to actually pin). In 'fixed'
  // mode (default, backwards-compatible) the panel claims `h-full` and
  // scrolls its inner content list internally.
  const rootClassName =
    layout === 'natural' ? 'flex flex-col' : 'h-full flex flex-col overflow-hidden';
  const bodyClassName =
    layout === 'natural' ? '' : 'flex-1 overflow-y-auto p-5';

  return (
    <div className={rootClassName}>
      <div className={bodyClassName}>
        <BuildingTabView
          buildingClass={buildingClass}
          projectType={projectType}
          subclasses={selectedSubclasses}
          scaleData={scaleData}
          complexity={complexity}
          workScope={workScope}
          complexityLevel={complexitySliderValue}
          scopeLevel={scopeSliderValue}
          onClassChange={(cls) => onClassChange?.(cls)}
          onTypeChange={(type) => selectType(type)}
          onSubclassToggle={handleSubclassToggle}
          onScaleChange={(key, value) => {
            setScaleData((prev) => {
              if (value === null) {
                if (!(key in prev)) return prev;
                const next = { ...prev };
                delete next[key];
                return next;
              }
              return { ...prev, [key]: value };
            });
          }}
          onComplexityChange={handleComplexityChange}
          onScopeToggle={handleScopeToggle}
          onComplexityLevelChange={handleComplexitySliderChange}
          onScopeLevelChange={handleScopeSliderChange}
          templates={derivedTemplates}
          complexityScore={complexityScore}
          complexityBand={complexityBand}
          riskFlags={riskFlags}
          disciplines={disciplines}
        />
      </div>
    </div>
  );
}
