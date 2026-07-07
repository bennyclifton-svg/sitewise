import type { GenomeEntry, GenomeFamily, GenomeLibrary, StyleGenome } from "@/lib/style-genome/types";

const genomeModules = import.meta.glob("./genomes/**/*.json", {
  eager: true,
  import: "default",
});

const families: GenomeFamily[] = ["historical", "modern", "regional", "invented"];

export const genomeEntries: GenomeEntry[] = Object.entries(genomeModules)
  .map(([path, value]) => toGenomeEntry(path, value))
  .sort((left, right) => {
    const familyDelta = families.indexOf(left.family) - families.indexOf(right.family);
    return familyDelta || left.label.localeCompare(right.label);
  });

export const genomeLibrary: GenomeLibrary = families.reduce(
  (library, family) => ({
    ...library,
    [family]: genomeEntries.filter((entry) => entry.family === family),
  }),
  {} as GenomeLibrary,
);

export function getGenomeEntry(id: string): GenomeEntry {
  const entry = genomeEntries.find((candidate) => candidate.id === id);
  if (!entry) {
    throw new Error(`Unknown style genome: ${id}`);
  }
  return entry;
}

function toGenomeEntry(path: string, value: unknown): GenomeEntry {
  const segments = path.split("/");
  const family = segments.at(-2);
  if (!isGenomeFamily(family)) {
    throw new Error(`Genome path must include a known family: ${path}`);
  }

  const genome = parseGenome(value, path);
  return {
    family,
    id: `${family}/${genome.period}`,
    label: toLabel(genome.period),
    genome,
  };
}

function parseGenome(value: unknown, path: string): StyleGenome {
  if (!isRecord(value)) throw new Error(`Genome must be an object: ${path}`);
  const massing = readRecord(value, "massing", path);
  const rhythm = readRecord(value, "rhythm", path);
  const ornament = readRecord(value, "ornament", path);
  const material = readRecord(value, "material", path);
  const motifs = readStringArray(ornament, "motifs", path);

  if (motifs.length < 1 || motifs.length > 3) {
    throw new Error(`Genome motifs must contain 1 to 3 entries: ${path}`);
  }

  return {
    period: readString(value, "period", path),
    massing: {
      footprint: readString(massing, "footprint", path) as StyleGenome["massing"]["footprint"],
      aspect: readAspect(massing, path),
      roof: readString(massing, "roof", path) as StyleGenome["massing"]["roof"],
      symmetry: readString(massing, "symmetry", path) as StyleGenome["massing"]["symmetry"],
    },
    rhythm: {
      bays: readNumber(rhythm, "bays", path),
      windowShape: readString(rhythm, "windowShape", path) as StyleGenome["rhythm"]["windowShape"],
      windowToWallRatio: readNumber(rhythm, "windowToWallRatio", path),
      verticality: readNumber(rhythm, "verticality", path),
    },
    ornament: {
      motifs: motifs as StyleGenome["ornament"]["motifs"],
      density: readNumber(ornament, "density", path),
    },
    material: {
      base: readString(material, "base", path),
      roughness: readNumber(material, "roughness", path),
      windowEmissive: readString(material, "windowEmissive", path),
    },
  };
}

function readRecord(record: Record<string, unknown>, key: string, path: string): Record<string, unknown> {
  const value = record[key];
  if (!isRecord(value)) throw new Error(`Missing object "${key}" in ${path}`);
  return value;
}

function readString(record: Record<string, unknown>, key: string, path: string): string {
  const value = record[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Missing string "${key}" in ${path}`);
  }
  return value;
}

function readNumber(record: Record<string, unknown>, key: string, path: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Missing number "${key}" in ${path}`);
  }
  return value;
}

function readStringArray(record: Record<string, unknown>, key: string, path: string): string[] {
  const value = record[key];
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error(`Missing string array "${key}" in ${path}`);
  }
  return value;
}

function readAspect(record: Record<string, unknown>, path: string): [number, number, number] {
  const value = record.aspect;
  if (!Array.isArray(value) || value.length !== 3 || value.some((item) => typeof item !== "number")) {
    throw new Error(`Genome aspect must be a 3-number tuple: ${path}`);
  }
  return value as [number, number, number];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isGenomeFamily(value: unknown): value is GenomeFamily {
  return typeof value === "string" && families.includes(value as GenomeFamily);
}

function toLabel(period: string): string {
  return period
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

