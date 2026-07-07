import type * as THREE from "three";

export type GenomeFamily = "historical" | "modern" | "regional" | "invented";

export type FootprintKind = "cruciform" | "rectangle" | "L" | "stepped" | "fractured";

export type RoofKind =
  | "spire"
  | "gable"
  | "hipped"
  | "flat"
  | "ziggurat"
  | "shed"
  | "curved"
  | "faceted";

export type SymmetryKind = "bilateral" | "asymmetric" | "radial";

export type WindowShape =
  | "lancet"
  | "sash"
  | "ribbon"
  | "porthole"
  | "slot"
  | "round_arch"
  | "screen"
  | "tall_rect"
  | "cellular"
  | "faceted";

export type StyleGenome = {
  period: string;
  massing: {
    footprint: FootprintKind;
    aspect: [number, number, number];
    roof: RoofKind;
    symmetry: SymmetryKind;
  };
  rhythm: {
    bays: number;
    windowShape: WindowShape;
    windowToWallRatio: number;
    verticality: number;
  };
  ornament: {
    motifs: [string, string?, string?];
    density: number;
  };
  material: {
    base: string;
    roughness: number;
    windowEmissive: string;
  };
};

export type GenomeEntry = {
  family: GenomeFamily;
  id: string;
  label: string;
  genome: StyleGenome;
};

export type GenomeLibrary = Record<GenomeFamily, GenomeEntry[]>;

export type BuildingUserData = {
  period: string;
  family?: GenomeFamily;
  seed: number;
  triangleCount: number;
  drawCallBudget: number;
  windowMaterials: THREE.MeshStandardMaterial[];
  rimMaterials: THREE.MeshStandardMaterial[];
  hoverTarget: number;
  hoverValue: number;
  baseY: number;
};
