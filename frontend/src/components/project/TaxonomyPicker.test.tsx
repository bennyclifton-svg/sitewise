import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  TaxonomyPicker,
  type TaxonomyPickerValue,
} from "@/components/project/TaxonomyPicker";
import type { TaxonomyCatalog } from "@/lib/types/project";

const catalog: TaxonomyCatalog = {
  work_types: [
    { value: "new", label: "New build" },
    { value: "refurb", label: "Refurbishment" },
    { value: "extend", label: "Extension / addition" },
    { value: "remediation", label: "Remediation / rectification" },
    { value: "advisory", label: "Advisory services" },
  ],
  building_classes: [
    classOption("residential", "Residential"),
    {
      value: "commercial",
      label: "Commercial",
      multi_subclass: false,
      work_types: ["new", "refurb"],
      subclasses: [
        {
          value: "office",
          label: "Office (Class 5)",
          ncc_class: "5",
          scale_fields: [
            {
              key: "nla_sqm",
              label: "NLA sqm",
              type: "number",
              typical: "1,000-80,000+ sqm NLA",
            },
          ],
        },
        { value: "other", label: "Other", ncc_class: "varies", scale_fields: [] },
      ],
    },
    classOption("industrial", "Industrial"),
    classOption("institution", "Institution"),
    {
      value: "mixed",
      label: "Mixed use",
      multi_subclass: true,
      work_types: ["new", "refurb"],
      subclasses: [
        {
          value: "residential_retail",
          label: "Residential + Retail",
          ncc_class: "2/6",
          scale_fields: [],
        },
        {
          value: "retail_office",
          label: "Retail + Office",
          ncc_class: "5/6",
          scale_fields: [],
        },
        { value: "other", label: "Other", ncc_class: "varies", scale_fields: [] },
      ],
    },
    classOption("infrastructure", "Infrastructure"),
  ],
  complexity_dimensions: {
    residential: complexityDimensions(),
    commercial: complexityDimensions(),
    industrial: complexityDimensions(),
    institution: complexityDimensions(),
    mixed: complexityDimensions(),
    infrastructure: complexityDimensions(),
  },
  risk_flags: {},
  work_scopes: {
    extend: {
      categories: [
        {
          value: "extension_interface",
          label: "Extension Interface",
          items: [
            {
              value: "structural_tie_in",
              label: "Structural Tie-In",
              consultants: ["Structural Engineer"],
            },
            {
              value: "weatherproofing_tie_in",
              label: "Weatherproofing Tie-In",
              consultants: ["Architect"],
            },
            {
              value: "services_connections",
              label: "Services Connections",
              consultants: ["Services Engineer"],
            },
            {
              value: "staged_occupation",
              label: "Staged Occupation",
              consultants: ["Project Manager"],
            },
          ],
        },
        {
          value: "site_works",
          label: "Site Works",
          items: [
            {
              value: "demolition",
              label: "Demolition",
              consultants: ["Demolition Consultant"],
            },
            {
              value: "temporary_works",
              label: "Temporary Works",
              consultants: ["Structural Engineer"],
            },
          ],
        },
      ],
    },
  },
  emphasis_profiles: { sections: [], base_weights: {}, modifiers: [] },
};

describe("TaxonomyPicker", () => {
  it("walks class to work type to subclass and scale, leaving complexity unstated", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    let latest: TaxonomyPickerValue = {};

    render(
      <ControlledPicker
        onChange={(value) => {
          latest = value;
          onChange(value);
        }}
      />,
    );

    expect(
      within(screen.getByLabelText("Building class")).getAllByRole("button"),
    ).toHaveLength(6);

    await user.click(screen.getByRole("button", { name: "Commercial" }));
    expect(screen.getByRole("button", { name: "New build" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Advisory services" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "New build" }));
    await user.click(screen.getByLabelText("Office (Class 5)"));
    await user.type(screen.getByLabelText("NLA sqm"), "1200");

    expect(screen.getByLabelText("NLA sqm")).toHaveAttribute(
      "placeholder",
      "1,000-80,000+ sqm NLA",
    );
    // An unanswered dimension must stay unanswered. Defaulting to the first
    // option asserted "vacant" on sites the user had not described yet.
    await waitFor(() =>
      expect(screen.getByLabelText("Operational constraints")).toHaveValue(""),
    );
    expect(latest).toMatchObject({
      building_class: "commercial",
      work_type: "new",
      subclasses: ["office"],
      scale: { nla_sqm: 1200 },
      complexity: {},
    });
    expect(onChange).toHaveBeenCalled();
  });

  it("records a complexity dimension only once the user picks one", async () => {
    const user = userEvent.setup();
    let latest: TaxonomyPickerValue = {};

    render(<ControlledPicker onChange={(value) => (latest = value)} />);

    await user.click(screen.getByRole("button", { name: "Commercial" }));
    await user.click(screen.getByRole("button", { name: "New build" }));

    expect(latest.complexity).toEqual({});

    await user.selectOptions(
      screen.getByLabelText("Operational constraints"),
      "live_environment",
    );

    expect(latest.complexity).toEqual({
      operational_constraints: "live_environment",
    });
  });

  it("clears a complexity dimension when returned to Not stated", async () => {
    const user = userEvent.setup();
    let latest: TaxonomyPickerValue = {};

    render(<ControlledPicker onChange={(value) => (latest = value)} />);

    await user.click(screen.getByRole("button", { name: "Commercial" }));
    await user.click(screen.getByRole("button", { name: "New build" }));
    await user.selectOptions(
      screen.getByLabelText("Operational constraints"),
      "live_environment",
    );
    expect(latest.complexity).toEqual({
      operational_constraints: "live_environment",
    });

    await user.selectOptions(screen.getByLabelText("Operational constraints"), "");

    expect(latest.complexity).toEqual({});
  });

  it("stores Other subclass free text as a labelled selection", async () => {
    const user = userEvent.setup();
    let latest: TaxonomyPickerValue = {};

    render(<ControlledPicker onChange={(value) => (latest = value)} />);

    await user.click(screen.getByRole("button", { name: "Commercial" }));
    await user.click(screen.getByRole("button", { name: "Refurbishment" }));
    await user.click(screen.getByLabelText("Other"));
    await user.type(screen.getByLabelText("Other subclass"), "Laboratory office");

    expect(latest.subclasses).toEqual([
      { value: "other", label: "Laboratory office" },
    ]);
  });

  it("uses checkboxes for mixed-use subclass selection", async () => {
    const user = userEvent.setup();
    let latest: TaxonomyPickerValue = {};

    render(<ControlledPicker onChange={(value) => (latest = value)} />);

    await user.click(screen.getByRole("button", { name: "Mixed use" }));
    await user.click(screen.getByRole("button", { name: "New build" }));
    await user.click(screen.getByLabelText("Residential + Retail"));
    await user.click(screen.getByLabelText("Retail + Office"));

    expect(screen.getByLabelText("Residential + Retail")).toBeChecked();
    expect(screen.getByLabelText("Retail + Office")).toBeChecked();
    expect(latest.subclasses).toEqual(["residential_retail", "retail_office"]);
  });

  it("shows scope expanded by default and stores selections", async () => {
    const user = userEvent.setup();
    let latest: TaxonomyPickerValue = {};

    render(<ControlledPicker onChange={(value) => (latest = value)} />);

    await user.click(screen.getByRole("button", { name: "Industrial" }));
    await user.click(screen.getByRole("button", { name: "Extension / addition" }));
    expect(screen.getByText("Scope")).toBeInTheDocument();
    expect(screen.getByLabelText("Structural Tie-In")).toBeVisible();
    await user.click(screen.getByLabelText("Structural Tie-In"));

    expect(latest.work_scope).toEqual(["structural_tie_in"]);
  });

  it("selects every item in a scope category from the category checkbox", async () => {
    const user = userEvent.setup();
    let latest: TaxonomyPickerValue = {};

    render(<ControlledPicker onChange={(value) => (latest = value)} />);

    await user.click(screen.getByRole("button", { name: "Industrial" }));
    await user.click(screen.getByRole("button", { name: "Extension / addition" }));
    await user.click(screen.getByLabelText("Demolition"));
    await user.click(screen.getByLabelText("Select all Extension Interface"));

    expect(screen.getByLabelText("Structural Tie-In")).toBeChecked();
    expect(screen.getByLabelText("Weatherproofing Tie-In")).toBeChecked();
    expect(screen.getByLabelText("Services Connections")).toBeChecked();
    expect(screen.getByLabelText("Staged Occupation")).toBeChecked();
    expect(screen.getByLabelText("Demolition")).toBeChecked();
    expect(screen.getByLabelText("Temporary Works")).not.toBeChecked();
    expect(screen.getByLabelText("Select all Extension Interface")).toBeChecked();
    expect(screen.getByLabelText("Select all Site Works")).not.toBeChecked();
    expect(latest.work_scope).toEqual([
      "demolition",
      "structural_tie_in",
      "weatherproofing_tie_in",
      "services_connections",
      "staged_occupation",
    ]);
  });

  it("clears the category checkbox when one item in the category is cleared", async () => {
    const user = userEvent.setup();
    let latest: TaxonomyPickerValue = {};

    render(<ControlledPicker onChange={(value) => (latest = value)} />);

    await user.click(screen.getByRole("button", { name: "Industrial" }));
    await user.click(screen.getByRole("button", { name: "Extension / addition" }));
    await user.click(screen.getByLabelText("Select all Extension Interface"));
    await user.click(screen.getByLabelText("Weatherproofing Tie-In"));

    expect(screen.getByLabelText("Weatherproofing Tie-In")).not.toBeChecked();
    expect(screen.getByLabelText("Structural Tie-In")).toBeChecked();
    expect(screen.getByLabelText("Select all Extension Interface")).not.toBeChecked();
    expect(screen.getByLabelText("Select all Extension Interface")).toHaveProperty(
      "indeterminate",
      true,
    );
    expect(latest.work_scope).toEqual([
      "structural_tie_in",
      "services_connections",
      "staged_occupation",
    ]);
  });

  it("clears a scope category when the category checkbox is unchecked", async () => {
    const user = userEvent.setup();
    let latest: TaxonomyPickerValue = {};

    render(<ControlledPicker onChange={(value) => (latest = value)} />);

    await user.click(screen.getByRole("button", { name: "Industrial" }));
    await user.click(screen.getByRole("button", { name: "Extension / addition" }));
    await user.click(screen.getByLabelText("Demolition"));
    await user.click(screen.getByLabelText("Select all Extension Interface"));
    await user.click(screen.getByLabelText("Select all Extension Interface"));

    expect(screen.getByLabelText("Structural Tie-In")).not.toBeChecked();
    expect(screen.getByLabelText("Staged Occupation")).not.toBeChecked();
    expect(screen.getByLabelText("Demolition")).toBeChecked();
    expect(screen.getByLabelText("Select all Extension Interface")).not.toBeChecked();
    expect(latest.work_scope).toEqual(["demolition"]);
  });

  it("uses zone titles for sections and quieter labels below the identity block", async () => {
    const user = userEvent.setup();

    render(
      <ControlledPicker
        onChange={() => undefined}
        budget=""
        onBudgetChange={() => undefined}
        scopeNarrative=""
        onScopeNarrativeChange={() => undefined}
      />,
    );

    expect(screen.getByRole("heading", { name: "Class" })).toHaveClass(
      "cockpit-zone-title",
    );

    await user.click(screen.getByRole("button", { name: "Industrial" }));
    expect(screen.getByRole("heading", { name: "Work type" })).toHaveClass(
      "cockpit-zone-title",
    );
    expect(screen.getByText("Budget")).toHaveClass(
      "text-xs",
      "text-muted-foreground",
    );

    await user.click(screen.getByRole("button", { name: "Extension / addition" }));
    expect(screen.getByRole("heading", { name: "Subclass" })).toHaveClass(
      "cockpit-zone-title",
    );
    expect(screen.getByRole("heading", { name: "Scale" })).toHaveClass(
      "cockpit-zone-title",
    );
    expect(screen.getByRole("heading", { name: "Complexity" })).toHaveClass(
      "cockpit-zone-title",
    );
    expect(screen.getByLabelText("Project profile")).toHaveClass(
      "border-t",
      "border-[var(--sw-edge)]",
    );
    expect(screen.getByText("Scope")).toHaveClass("cockpit-zone-title");
    expect(screen.getByText("Scope notes")).toHaveClass(
      "text-xs",
      "text-muted-foreground",
    );
  });

  it("places budget beside work type and scope notes below the lists", async () => {
    const user = userEvent.setup();
    const onBudgetChange = vi.fn();
    const onScopeNarrativeChange = vi.fn();

    render(
      <ControlledPicker
        onChange={() => undefined}
        budget=""
        onBudgetChange={onBudgetChange}
        scopeNarrative=""
        onScopeNarrativeChange={onScopeNarrativeChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Industrial" }));
    expect(
      within(screen.getByLabelText("Work type")).getByLabelText("Budget"),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Scope notes")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Extension / addition" }));
    const scope = screen.getByRole("region", { name: "Scope" });
    expect(within(scope).getByLabelText("Structural Tie-In")).toBeInTheDocument();
    expect(within(scope).getByLabelText("Scope notes")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Budget"), "$4m");
    const scopeNotes = screen.getByLabelText("Scope notes");
    expect(scopeNotes).toHaveClass("overflow-hidden", "resize-none");
    await user.type(scopeNotes, "Rooftop solar");
    expect(onBudgetChange).toHaveBeenCalled();
    expect(onScopeNarrativeChange).toHaveBeenCalled();
  });

  it("does not clear work type or subclass when the selected class is clicked again", async () => {
    const user = userEvent.setup();
    let latest: TaxonomyPickerValue = {};

    render(<ControlledPicker onChange={(value) => (latest = value)} />);

    await user.click(screen.getByRole("button", { name: "Infrastructure" }));
    await user.click(screen.getByRole("button", { name: "Refurbishment" }));
    await user.click(screen.getByLabelText("Infrastructure standard"));
    await user.click(screen.getByRole("button", { name: "Infrastructure" }));

    expect(latest).toMatchObject({
      building_class: "infrastructure",
      work_type: "refurb",
      subclasses: ["infrastructure_standard"],
    });
    expect(screen.getByRole("button", { name: "Refurbishment" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});

function ControlledPicker({
  onChange,
  budget,
  onBudgetChange,
  scopeNarrative,
  onScopeNarrativeChange,
}: {
  onChange: (value: TaxonomyPickerValue) => void;
  budget?: string;
  onBudgetChange?: (value: string) => void;
  scopeNarrative?: string;
  onScopeNarrativeChange?: (value: string) => void;
}) {
  const [value, setValue] = useState<TaxonomyPickerValue>({});
  return (
    <TaxonomyPicker
      catalog={catalog}
      value={value}
      onChange={(next) => {
        setValue(next);
        onChange(next);
      }}
      budget={budget}
      onBudgetChange={onBudgetChange}
      scopeNarrative={scopeNarrative}
      onScopeNarrativeChange={onScopeNarrativeChange}
    />
  );
}

function classOption(value: string, label: string) {
  return {
    value,
    label,
    multi_subclass: false,
    work_types: ["new", "refurb", "extend", "remediation", "advisory"],
    subclasses: [
      {
        value: `${value}_standard`,
        label: `${label} standard`,
        ncc_class: "varies",
        scale_fields: [],
      },
      { value: "other", label: "Other", ncc_class: "varies", scale_fields: [] },
    ],
  };
}

function complexityDimensions() {
  return [
    {
      key: "operational_constraints",
      label: "Operational constraints",
      options: [
        { value: "vacant", label: "Vacant/Unoccupied" },
        { value: "live_environment", label: "Live Environment (+10-20%)" },
      ],
    },
  ];
}
