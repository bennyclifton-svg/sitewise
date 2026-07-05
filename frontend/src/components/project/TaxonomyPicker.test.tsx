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
  work_scopes: {},
  emphasis_profiles: { sections: [], base_weights: {}, modifiers: [] },
};

describe("TaxonomyPicker", () => {
  it("walks class to work type to subclass, scale, and default complexity", async () => {
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
    await waitFor(() =>
      expect(screen.getByLabelText("Operational constraints")).toHaveValue("vacant"),
    );
    expect(latest).toMatchObject({
      building_class: "commercial",
      work_type: "new",
      subclasses: ["office"],
      scale: { nla_sqm: 1200 },
      complexity: {
        operational_constraints: "vacant",
      },
    });
    expect(onChange).toHaveBeenCalled();
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
});

function ControlledPicker({
  onChange,
}: {
  onChange: (value: TaxonomyPickerValue) => void;
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
