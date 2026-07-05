The current project management and plan framework is not providing a lot of value to the user, I want to re factor and rethink this project management plan approach and outcome. 

We need to hold onto the concept of the agent doing a document sweep every time the user updates the PMP, whereby it goes back and reviews all the new doc... documents that have been added to the document repository and then just extracts what is required from those documents to then update and populate the PMP. So the PMP should be thought of as a live document, which will be updated all the time, work in progress by the user throughout the whole life of the project. It's not just a document created at the beginning. So this document will be at one end of the spectrum created with very little information. It might be user just saying this is... I'm doing a house, class one a. It's a new build, and I've got a budget of a million dollars. That might be the extent of their brief. But at the other end of the spectrum, you might have a project that's doing a commercial project that may have a hundred documents that they upload and ingest, and then the agent must go through every... all one hundred documents and decipher what information is required. So it's quite a broad complex proposition that I'm putting forward here, but take this thought first and foremost and then moving on to objective one, which is detailed a bit bit below this creating, um, some sort of interactivity for... with the the PMP. Objective two is the extend beyond the the repo's current residential focus into a a full industrial, commercial institution mixed. And then the fourth... oh, sorry. The third objective is to... it's got some sort of prior research and specifications that I've dumped into this file just to help, um, with this current planning phase.

Feel free to discard any of the information in this p m p two file that you do not think is useful. There is some syntax and TypeScript and other stuff in here which I have just dumped and not considered with... in too much detail. Just extract out the important context to achieve the objectives. 

## Objective 1 - 
Create a concise project management plan that is suited to the user. What I envisage is a plan that is perhaps rendered in HTML with tables lots of tables and, um, visual cues to allow the user to quickly understand where the project is up to. The PMP must be structured chronologically as the project is developed. And I like the idea of having HTML so the user can... if if the AI agent has made a selection for a particular element within the project management pan, and it's just one of many options to be selected, and it may be the incorrect selection or the chew... the user just may choose to override it. Um, they have the option to toggle or... and make an alternate selection on the fly, and that selection becomes persistent and is retained. So that's the first concept I'm looking for, a semi interactive, um, project management plan instead of just rendering a static markdown file. We're going to render a dynamic HTML file, which the user can interact with. And the other thing they can do is actually modify the the wording in the report. So For example, the AI agent might have three items describing the kitchen. The user will read those three items and intuitively think, oh, and I also want these types of handles or this type of door closing mechanism. So it allows the user to quickly and interactively update the PMP. That's the first and most fundamental item here. Second,

##Objective 2
The second change I wanna make is to extend beyond residential to intercommercial, industrial, institutional, mixed, and infrastructure. Matrixed with the the work type that is being performed as refurbishment, extension, new remediation, and and advisory. So this will need to be considered, um, and will input... impact the existing repo because currently, the repo is geared up with just residential. and the subsets of residential or extension, um, new, and I think, um, refurbishment. I can't remember exactly. So, anyway, we've gotta expand the breadth of this gut... of this whole application to cover off those other classes.

'refurb',
'extend',
'new',
'remediation',
'advisory'

'residential',
'commercial',
'industrial',
'institution',
'mixed',
'infrastructure',

Refer to additional knowledge seeds in a folder called, data/seed-commercial.

  cost-management-principles.md
  procurement-tendering-guide.md
  contract-administration-guide.md
  program-scheduling-guide.md
  ncc-reference-guide.md
  as-standards-reference.md
  residential-construction-guide.md
  multi-residential-apartments-guide.md
  commercial-construction-guide.md
  remediation-due-diligence-guide.md


## Objective 3 
The third objective is to introduce the concept of a subclass, scale, complexity, and scope. So I've added in the briefing document p and p two, um, assortment of different spec material that I've prepared and used in previous projects, which you should use to help with sort of research and design and development of this new feature, and it covers off the... it's already done some research about what the subclasses building classes are in the Australian, um, construction industry, the types of scales that we should be considering for each different project type, um, and then the complexity dimensions. Now this is a concept which is new, and I think it's really good. But, basically, for each different building class, um, project type, there are different types of complexity factors that come into play. So review these, and by all means, improve them, add to them, and make them tighter and more com... complete and whole.



### 3.2 Middle Panel: Subclass/Scale/Complexity

After Class + Type selection, Middle Panel displays 3 columns:

#### Column 1: Subclass (Context-Dependent)

| Building Class | Subclass Options |
|----------------|------------------|
| **Residential** | House (Class 1a), Apartments (Class 2), Townhouses (Class 1a), BTR (Build-to-Rent), Student Housing (PBSA), **Retirement Living / ILUs**, **Residential Aged Care (Class 9c)**, Social/Affordable Housing, Other |
| **Commercial** | Office (Class 5), Retail - Shopping Centre (Class 6), Retail - Standalone (Class 6), Hotel (Class 3), Food & Beverage (Class 6), Serviced Office/Coworking, Other |
| **Industrial** | Warehouse (Class 7b), Logistics/E-Commerce (Class 7b), Manufacturing (Class 8), Cold Storage (Class 7b), Data Centre (Class 7b), Dangerous Goods (Class 7a), Other |
| **Institution** | Education - Early Childhood, Education - Primary/Secondary (Class 9b), Education - Tertiary (Class 9b), Healthcare - Hospital (Class 9a), Healthcare - Medical Centre, Healthcare - Clinic/Allied, Government/Civic, Religious (Class 9b), Other |
| **Mixed** | Residential + Retail, Residential + Commercial, Hotel + Residential, Retail + Office, Build-to-Rent + Retail, Vertical Village (ILU + Aged Care), Other |
| **Infrastructure** | Roads/Highways, Rail/Metro, Water/Utilities, Energy/Renewables, Marine/Ports, Airports, Telecommunications, Other |

**Rules:**
- Always includes "Other" option with free-text input
- **Single selection for most classes; MULTIPLE selection allowed for Mixed class**
- Options load dynamically from configuration
- "Other" selections stored for AI learning (pattern analysis over time)

#### Column 2: Scale

Based on Australian construction industry standards (NCC/BCA, AIQS, Rawlinsons 2025):

**RESIDENTIAL**
| Subclass | Scale Inputs | Typical Ranges |
|----------|--------------|----------------|
| **House (Class 1a)** | GFA m², Storeys, Bedrooms, Garage Spaces | 50-800m²; 1-3 storeys; 2-6 bed |
| **Apartments (Class 2)** | Storeys, GFA m², Units, Avg Unit Size m² | Low-rise 1-3, Mid-rise 4-12, High-rise 13-40, Super-tall 40+; 50-150m²/unit |
| **Townhouses** | Dwellings, GFA m², Avg Dwelling Size m² | 3-50 dwellings; 120-250m² each |
| **BTR (Build-to-Rent)** | Storeys, Units, Amenity GFA m², Unit Mix (Studio/1B/2B/3B %) | 100-500+ units; 5-10% amenity; 15/40/35/10% typical mix |
| **Student Housing (PBSA)** | Beds, Cluster Apartments, GFA m², Common Area m² | 200-1000+ beds; 4-8 beds per cluster |
| **Retirement Living / ILUs** | ILUs (count), GFA m², Serviced Apartments, Community Facilities m², Avg ILU Size m² | 20-300+ ILUs; 60-120m² per ILU; Serviced 40-80m² |
| **Aged Care (Class 9c)** | Beds, Dementia Beds, GFA m², GFA/Bed m², Households/Wings, Beds/Household | 60-150 beds; 50-80m²/bed; 10-16 beds/household |

**COMMERCIAL**
| Subclass | Scale Inputs | Typical Ranges |
|----------|--------------|----------------|
| **Office (Class 5)** | Storeys, NLA m², Floor Plate m², Tenancies, Grade (B/A/Premium/Trophy) | 1,000-80,000+ m² NLA; 500-2,500m² floor plates |
| **Retail - Shopping Centre** | GLA m², Major Anchors, Specialties, Levels, Car Parks | Neighbourhood 5-15k, Sub-regional 15-40k, Regional 40-100k+ m² |
| **Retail - Standalone** | GLA m², Frontage m, Car Parks | 200-5,000m²; 10-50m frontage |
| **Hotel (Class 3)** | Rooms, Storeys, Star Rating (3-5★), F&B Outlets, Meeting/Conference m² | Budget 30-100, Midscale 100-250, Upscale 150-400, Luxury 80-250 rooms |
| **Food & Beverage** | Seats, GFA m², Kitchen m², Liquor License Type | 20-400 seats; kitchen 15-25% of GFA |

**INDUSTRIAL**
| Subclass | Scale Inputs | Typical Ranges |
|----------|--------------|----------------|
| **Warehouse (Class 7b)** | GFA m², Clear Height m, Dock Doors, Hardstand m², Office % | 2,000-75,000+ m²; 8-15m+ height; 3-10% office |
| **Logistics/E-Commerce** | GFA m², Clear Height m, Dock Doors, Cross-dock Bays, Automation Level | 10,000-100,000+ m²; 12-18m height; high dock ratio |
| **Manufacturing (Class 8)** | GFA m², Process Area m², Cleanroom Class (ISO 5-8), Crane Capacity t | 1,000-50,000m²; crane 5-50t |
| **Cold Storage** | GFA m², Frozen m² (<-18°C), Chilled m² (0-4°C), Ambient m², Blast Freezer Capacity t/day | 2,000-30,000m²; 2-3x standard cost |
| **Data Centre** | IT Load MW, Total GFA m², White Space m², PUE Target, Redundancy Tier (1-4) | 1-50+ MW; PUE 1.2-1.6; $15-25k/m² |

**INSTITUTION**
| Subclass | Scale Inputs | Typical Ranges |
|----------|--------------|----------------|
| **Education - Early Childhood** | Places, GFA m², Indoor m²/child, Outdoor m²/child | 30-120 places; 3.25m² indoor; 7m² outdoor min |
| **Education - Primary/Secondary** | Students, GFA m², Classrooms, Specialist Rooms, Halls/Gyms, Playing Fields | 300-2,000 students; 10-15m²/student |
| **Education - Tertiary** | Students (FTE), GFA m², Lecture Theatres, Labs, Library m² | 1,000-50,000 FTE; 15-25m²/student |
| **Healthcare - Hospital (Class 9a)** | Beds, GFA m², ED Bays, Operating Theatres, ICU Beds, Car Parks | 50-800+ beds; 100-150m²/bed; 2.5-4 parks/bed |
| **Healthcare - Medical Centre** | Consulting Rooms, GFA m², Procedure Rooms, Imaging Suites | 5-50 rooms; 25-40m²/room |
| **Healthcare - Clinic/Allied** | Practitioners, GFA m², Treatment Rooms | 2-20 practitioners; 60-100m²/practitioner |
| **Government/Civic** | GFA m², Public Areas m², Secure Areas m², Staff Count | 1,000-50,000m²; security zoning critical |
| **Religious** | Seats, GFA m², Ancillary Halls m², Car Parks | 100-2,000+ seats; 0.8-1.2m²/seat |

**MIXED USE**
| Subclass | Scale Inputs | Typical Ranges |
|----------|--------------|----------------|
| **All Mixed Types** | Total Storeys, Total GFA m², Podium Levels, Tower Levels | 5-80+ storeys |
| | Residential: Units, Avg Size m² | 50-500 units |
| | Commercial: NLA m², Tenancies | 1,000-20,000m² |
| | Retail: GLA m², Anchors | 500-10,000m² |
| | Hotel: Rooms (if applicable) | 100-300 rooms |
| | Car Parks (shared/allocated) | 0.5-1.5 per residential, 1:40m² commercial |

**INFRASTRUCTURE**
| Subclass | Scale Inputs | Typical Ranges |
|----------|--------------|----------------|
| **Roads/Highways** | Length km, Lanes, Interchanges, Bridges/Tunnels, Pavement Type | 1-100+ km; 2-8 lanes |
| **Rail/Metro** | Length km, Stations, Rolling Stock Bays, Stabling, Tunnel km | 5-50+ km; 2-20+ stations |
| **Water/Utilities** | Capacity ML/day, Pipeline km, Pump Stations, Reservoirs ML | 10-1,000+ ML/day |
| **Energy/Renewables** | Capacity MW, Panels/Turbines, Battery Storage MWh, Substation | Solar 1-500MW, Wind 10-1,000MW |
| **Marine** | Berths, Quay Length m, Draft m, Container TEU, Passenger Capacity | 2-50 berths; 8-18m draft |


  New Risk Flags


  Universal Complexity Dimensions

Add to every building class's `complexityOptions.default`:

```json
{
  "contamination_level": [
    { "value": "nil", "label": "Nil/Clean Site" },
    { "value": "minor", "label": "Minor (Spot Treatment)" },
    { "value": "significant", "label": "Significant (+10-20%)" },
    { "value": "heavily_contaminated", "label": "Heavily Contaminated (+30-50%)" }
  ],
  "access_constraints": [
    { "value": "unrestricted", "label": "Unrestricted Access" },
    { "value": "urban_constrained", "label": "Urban/Constrained" },
    { "value": "restricted_hours", "label": "Restricted Hours" },
    { "value": "remote", "label": "Remote Site (+15-30%)" }
  ],
  "operational_constraints": [
    { "value": "vacant", "label": "Vacant/Unoccupied" },
    { "value": "partial_occupation", "label": "Partial Occupation" },
    { "value": "live_environment", "label": "Live Environment (+10-20%)" },
    { "value": "24_7_occupied", "label": "24/7 Occupied (+20-30%)" }
  ],
  "procurement_route": [
    { "value": "traditional", "label": "Traditional (Lump Sum)" },
    { "value": "design_construct", "label": "Design & Construct" },
    { "value": "eci", "label": "Early Contractor Involvement" },
    { "value": "managing_contractor", "label": "Managing Contractor" },
    { "value": "alliance", "label": "Alliance (+5-10%)" },
    { "value": "ppp", "label": "PPP" }
  ],
  "stakeholder_complexity": [
    { "value": "single_owner", "label": "Single Owner" },
    { "value": "strata", "label": "Strata Ownership" },
    { "value": "government", "label": "Government Client" },
    { "value": "multiple_agencies", "label": "Multiple Agencies (+10-20%)" }
  ],
  "environmental_sensitivity": [
    { "value": "standard", "label": "Standard" },
    { "value": "sensitive", "label": "Environmentally Sensitive" },
    { "value": "protected_habitat", "label": "Protected Habitat (+20%)" },
    { "value": "aboriginal_heritage", "label": "Aboriginal Heritage (+15%)" }
  ]

**Priority:** MEDIUM | **Impact:** MEDIUM | **Effort:** LOW

Add to `workScopeOptions.riskDefinitions`:

```json
{
  "high_security": {
    "severity": "warning",
    "title": "High Security Classification",
    "description": "Top Secret/SCI facilities require SCIF construction, cleared workforce, and extended approval timelines."
  },
  "remote_site": {
    "severity": "warning",
    "title": "Very Remote Location",
    "description": "Very remote sites add 40%+ to construction costs. Consider modular/prefabrication strategies."
  },
  "live_operations": {
    "severity": "info",
    "title": "Live Operational Environment",
    "description": "Works in live environments require careful staging, safety protocols, and operational coordination."
  },
  "biosafety_3_plus": {
    "severity": "critical",
    "title": "BSL-3+ Laboratory",
    "description": "High containment laboratories require specialized design, certification, and security protocols."
  },
  "gmp_manufacturing": {
    "severity": "warning",
    "title": "GMP Manufacturing",
    "description": "Good Manufacturing Practice facilities require validation protocols and TGA/FDA compliance pathways."
  },
  "heritage_adaptive_reuse": {
    "severity": "warning",
    "title": "Heritage Adaptive Reuse",
    "description": "Adaptive reuse of heritage buildings requires heritage consultant, conservation management plan, and approvals."
  },
  "critical_infrastructure": {
    "severity": "warning",
    "title": "Critical Infrastructure",
    "description": "Critical infrastructure projects require SOCI Act compliance and enhanced security measures."
  },
  "multi_jurisdictional": {
    "severity": "info",
    "title": "Multi-Jurisdictional",
    "description": "Projects spanning jurisdictions require coordination across multiple regulatory frameworks."
  },
  "native_title": {
    "severity": "warning",
    "title": "Native Title Considerations",
    "description": "Sites with native title claims require Indigenous Land Use Agreement (ILUA) or consent processes."
  },
  "flood_overlay": {
    "severity": "warning",
    "title": "Flood Overlay",
    "description": "Flood-prone land requires hydraulic study, flood-compatible design, and resilience measures."



    ## 5. Phase 4: Work Scope Expansion (NEW and ADVISORY)

**Priority:** HIGH | **Impact:** HIGH | **Effort:** MEDIUM

Currently work scope only exists for refurb, remediation, extend. This adds comprehensive work scope definitions for NEW and ADVISORY project types.

### 5.1 Work Scope for NEW Builds

```json
"new": {
  "enabling_works": {
    "label": "Enabling Works",
    "items": [
      { "value": "demolition", "label": "Demolition", "consultants": ["Demolition Consultant", "Hazmat Consultant"] },
      { "value": "site_clearance", "label": "Site Clearance", "consultants": ["Civil Engineer"] },
      { "value": "decontamination", "label": "Decontamination", "consultants": ["Environmental Consultant"], "riskFlag": "contaminated_land" },
      { "value": "bulk_earthworks", "label": "Bulk Earthworks", "consultants": ["Civil Engineer", "Geotechnical Engineer"] },
      { "value": "temporary_works", "label": "Temporary Works", "consultants": ["Structural Engineer"] },
      { "value": "utility_diversions", "label": "Utility Diversions", "consultants": ["Civil Engineer", "Services Engineer"] }
    ]
  },
  "civil_works": {
    "label": "Civil Works",
    "items": [
      { "value": "earthworks_detailed", "label": "Detailed Earthworks", "consultants": ["Civil Engineer"] },
      { "value": "site_drainage", "label": "Site Drainage", "consultants": ["Civil Engineer", "Hydraulic Engineer"] },
      { "value": "stormwater_management", "label": "Stormwater Management", "consultants": ["Civil Engineer"] },
      { "value": "internal_roads", "label": "Internal Roads/Pavements", "consultants": ["Civil Engineer", "Traffic Engineer"] },
      { "value": "retaining_walls", "label": "Retaining Walls", "consultants": ["Structural Engineer", "Civil Engineer"] }
    ]
  },
  "structure": {
    "label": "Structure",
    "items": [
      { "value": "substructure", "label": "Substructure/Foundations", "consultants": ["Structural Engineer", "Geotechnical Engineer"] },
      { "value": "superstructure", "label": "Superstructure", "consultants": ["Structural Engineer"] },
      { "value": "post_tensioning", "label": "Post-Tensioning", "consultants": ["Structural Engineer"], "complexityPoints": 1 },
      { "value": "precast_elements", "label": "Precast Elements", "consultants": ["Structural Engineer"] },
      { "value": "steel_frame", "label": "Structural Steel Frame", "consultants": ["Structural Engineer"] },
      { "value": "timber_mass", "label": "Mass Timber Structure", "consultants": ["Structural Engineer", "Fire Engineer"], "complexityPoints": 2 }
    ]
  },
  "envelope": {
    "label": "Building Envelope",
    "items": [
      { "value": "facade_system", "label": "Facade System", "consultants": ["Facade Engineer", "Architect"] },
      { "value": "curtain_wall", "label": "Curtain Wall", "consultants": ["Facade Engineer"] },
      { "value": "roofing", "label": "Roofing System", "consultants": ["Architect"] },
      { "value": "glazing", "label": "Glazing/Windows", "consultants": ["Facade Engineer"] },
      { "value": "waterproofing", "label": "Waterproofing", "consultants": ["Waterproofing Consultant"] }
    ]
  },
  "services": {
    "label": "Building Services",
    "items": [
      { "value": "mechanical_hvac", "label": "Mechanical/HVAC", "consultants": ["Services Engineer (Mechanical)"] },
      { "value": "electrical_power", "label": "Electrical/Power", "consultants": ["Services Engineer (Electrical)"] },
      { "value": "hydraulic_plumbing", "label": "Hydraulic/Plumbing", "consultants": ["Services Engineer (Hydraulic)"] },
      { "value": "fire_services", "label": "Fire Services", "consultants": ["Fire Engineer"] },
      { "value": "vertical_transport", "label": "Vertical Transport", "consultants": ["Vertical Transport Consultant"] },
      { "value": "bms_controls", "label": "BMS/Controls", "consultants": ["BMS Consultant"] },
      { "value": "security_systems", "label": "Security Systems", "consultants": ["Security Consultant"] },
      { "value": "ict_structured_cabling", "label": "ICT/Structured Cabling", "consultants": ["ICT Consultant"] }
    ]
  },
  "fitout": {
    "label": "Internal Fitout",
    "items": [
      { "value": "partitions_walls", "label": "Partitions/Internal Walls", "consultants": ["Architect"] },
      { "value": "ceilings", "label": "Ceilings", "consultants": ["Architect"] },
      { "value": "flooring", "label": "Flooring", "consultants": ["Architect", "Interior Designer"] },
      { "value": "joinery", "label": "Joinery/Cabinetry", "consultants": ["Interior Designer"] },
      { "value": "specialist_fitout", "label": "Specialist Fitout (Lab/Kitchen)", "consultants": ["Specialist Consultant"], "complexityPoints": 1 }
    ]
  },
  "external_works": {
    "label": "External Works",
    "items": [
      { "value": "landscaping", "label": "Landscaping", "consultants": ["Landscape Architect"] },
      { "value": "car_parking", "label": "Car Parking", "consultants": ["Civil Engineer", "Traffic Engineer"] },
      { "value": "signage_wayfinding", "label": "Signage/Wayfinding", "consultants": ["Signage Consultant"] },
      { "value": "external_lighting", "label": "External Lighting", "consultants": ["Lighting Designer"] },
      { "value": "fencing_gates", "label": "Fencing/Gates", "consultants": ["Security Consultant", "Architect"] }
    ]
  }
}
```

### 5.2 Work Scope for ADVISORY Projects

```json
"advisory": {
  "due_diligence": {
    "label": "Due Diligence",
    "items": [
      { "value": "technical_dd", "label": "Technical Due Diligence", "consultants": ["Building Consultant", "Structural Engineer"] },
      { "value": "building_condition", "label": "Building Condition Assessment", "consultants": ["Building Consultant"] },
      { "value": "environmental_dd", "label": "Environmental Due Diligence", "consultants": ["Environmental Consultant"] },
      { "value": "compliance_audit", "label": "Compliance Audit", "consultants": ["Building Certifier", "Fire Engineer"] },
      { "value": "capex_assessment", "label": "CapEx Assessment", "consultants": ["Quantity Surveyor"] },
      { "value": "services_assessment", "label": "Services Assessment", "consultants": ["Services Engineer"] }
    ]
  },
  "feasibility": {
    "label": "Feasibility Studies",
    "items": [
      { "value": "highest_best_use", "label": "Highest & Best Use Study", "consultants": ["Town Planner", "Architect"] },
      { "value": "development_feasibility", "label": "Development Feasibility", "consultants": ["Quantity Surveyor", "Town Planner"] },
      { "value": "massing_study", "label": "Massing/Yield Study", "consultants": ["Architect", "Town Planner"] },
      { "value": "cost_benefit", "label": "Cost-Benefit Analysis", "consultants": ["Quantity Surveyor"] }
    ]
  },
  "design_review": {
    "label": "Design Review",
    "items": [
      { "value": "design_audit", "label": "Design Audit", "consultants": ["Project Manager", "Architect"] },
      { "value": "value_engineering", "label": "Value Engineering", "consultants": ["Quantity Surveyor", "Architect"] },
      { "value": "constructability_review", "label": "Constructability Review", "consultants": ["Construction Manager"] },
      { "value": "peer_review", "label": "Peer Review (Structural/Services)", "consultants": ["Structural Engineer", "Services Engineer"] }
    ]
  },
  "procurement_support": {
    "label": "Procurement Support",
    "items": [
      { "value": "procurement_strategy", "label": "Procurement Strategy", "consultants": ["Project Manager"] },
      { "value": "tender_documentation", "label": "Tender Documentation Review", "consultants": ["Quantity Surveyor"] },
      { "value": "tender_evaluation", "label": "Tender Evaluation", "consultants": ["Quantity Surveyor", "Project Manager"] },
      { "value": "contract_negotiation", "label": "Contract Negotiation Support", "consultants": ["Project Manager"] }
    ]
  },
  "contract_administration": {
    "label": "Contract Administration",
    "items": [
      { "value": "superintendent_services", "label": "Superintendent Services", "consultants": ["Project Manager"] },
      { "value": "progress_certification", "label": "Progress Certification", "consultants": ["Quantity Surveyor"] },
      { "value": "variation_assessment", "label": "Variation Assessment", "consultants": ["Quantity Surveyor"] },
      { "value": "eot_assessment", "label": "EOT Assessment", "consultants": ["Project Manager", "Programming Consultant"] },
      { "value": "defects_management", "label": "Defects Management", "consultants": ["Project Manager"] }
    ]
  },
  "dispute_resolution": {
    "label": "Dispute Resolution",
    "items": [
      { "value": "claim_assessment", "label": "Claim Assessment", "consultants": ["Quantity Surveyor"], "complexityPoints": 2 },
      { "value": "delay_analysis", "label": "Delay Analysis", "consultants": ["Programming Consultant"], "complexityPoints": 2 },
      { "value": "expert_determination", "label": "Expert Determination", "consultants": ["Expert Witness"], "complexityPoints": 3 },
      { "value": "arbitration_support", "label": "Arbitration/Litigation Support", "consultants": ["Expert Witness"], "complexityPoints": 3 }
    ]
  }
}


Complexity Options

```json
"agricultural": {
  "complexityOptions": {
    "default": {
      "water_source": [
        { "value": "town_water", "label": "Town Water" },
        { "value": "bore", "label": "Bore/Groundwater" },
        { "value": "dam_catchment", "label": "Dam/Catchment" },
        { "value": "river_allocation", "label": "River Allocation" },
        { "value": "recycled", "label": "Recycled Water" }
      ],
      "power_source": [
        { "value": "grid", "label": "Grid Connected" },
        { "value": "off_grid_solar", "label": "Off-Grid Solar" },
        { "value": "hybrid", "label": "Hybrid (Grid + Solar)" },
        { "value": "diesel_backup", "label": "Diesel Backup Required" }
      ],
      "remoteness": [
        { "value": "peri_urban", "label": "Peri-Urban" },
        { "value": "regional", "label": "Regional" },
        { "value": "remote", "label": "Remote (+20%)" },
        { "value": "very_remote", "label": "Very Remote (+40%)" }
      ],
      "environmental": [
        { "value": "standard", "label": "Standard" },
        { "value": "waterway_buffer", "label": "Waterway Buffer Zone" },
        { "value": "vegetation_clearing", "label": "Vegetation Clearing Required" },
        { "value": "protected_habitat", "label": "Protected Habitat (+30%)" }
      ]
    }
  }
}
```

### 2.3 Industrial Additions (+6 subclasses)

Add to `buildingClasses.industrial.subclasses`:

```json
{ "value": "heavy_manufacturing", "label": "Heavy Manufacturing (Foundry/Smelter)" },
{ "value": "food_processing", "label": "Food Processing / Cold Chain" },
{ "value": "pharmaceutical_gmp", "label": "Pharmaceutical/GMP Manufacturing" },
{ "value": "cleanroom", "label": "Clean Rooms (ISO Grade)" },
{ "value": "battery_manufacturing", "label": "Battery Manufacturing / Energy Storage" },
{ "value": "waste_to_energy", "label": "Waste-to-Energy Facility" }
```

**Scale Fields for Cleanroom:**

```json
[
  { "key": "cleanroom_sqm", "label": "Cleanroom Area (m²)", "placeholder": "500-10000" },
  { "key": "iso_class", "label": "ISO Class", "type": "integer", "min": 4, "max": 8 },
  { "key": "gfa_sqm", "label": "Total GFA (m²)", "placeholder": "1000-50000" },
  { "key": "change_rooms", "label": "Gowning/Change Rooms", "type": "integer" }
]
```

**Complexity Options for Cleanroom:**

```json
"cleanroom": {
  "iso_class": [
    { "value": "iso_8", "label": "ISO 8 (100,000 particles)" },
    { "value": "iso_7", "label": "ISO 7 (10,000 particles)" },
    { "value": "iso_6", "label": "ISO 6 (1,000 particles) (+30%)" },
    { "value": "iso_5", "label": "ISO 5 (100 particles) (+50%)" },
    { "value": "iso_4", "label": "ISO 4 (10 particles) (+100%)" }

FUNCTIONAL & QUALITY — What the building provides and how well:
- Physical attributes (bedrooms, floors, spaces, areas)
- Design features (open plan, layout, configuration)
- Operational requirements (storage, parking, amenities)
- Quality/finish standards (premium finishes, materials, fixtures)
- Performance requirements (acoustic, thermal, structural)
- User experience (accessibility features, natural light)
Headers to use: Design Requirements, Quality Standards, Operational Requirements

PLANNING & COMPLIANCE — Approvals, regulations, and certifications needed:
- Building codes (NCC, BCA classification)
- Regulatory approvals (DA, CDC, permits)
- Australian Standards (AS 2419.1, AS 3959, etc.)
- Certifications required (BASIX, NatHERS, fire engineering)
- Authority requirements (council, fire brigade, utilities)
- Environmental compliance (contamination, stormwater)
Headers to use: Regulatory Compliance, Certification Requirements, Authority Approvals

  ## 2. Australian Building Codes and Standards Research

### 2.1 National Construction Code (NCC)

The NCC is the primary regulatory framework for building in Australia, maintained by the Australian Building Codes Board (ABCB).

**Structure:**
- **Volume 1**: Commercial buildings (Class 2-9)
- **Volume 2**: Residential buildings (Class 1 and 10)
- **Volume 3**: Plumbing and drainage

**Performance-based framework:** The NCC uses a hierarchy of Performance Requirements (mandatory outcomes), Deemed-to-Satisfy (DtS) Provisions (prescriptive compliance paths), and Verification Methods (alternative compliance pathways).

**Access and licensing:**
- Free digital access since 2019 at ncc.abcb.gov.au
- Can quote individual clauses with attribution
- Cannot replicate entire code sections or DtS tables
- Updated every 3 years (latest NCC 2022, effective May 2023)

**State variations are critical:** Each state and territory can amend the NCC with local additions. These variations must be tracked:

| State | Authority | Key Additions |
|-------|-----------|---------------|
| NSW | NSW Fair Trading / Building Commissioner | BASIX energy/water targets, Design & Building Practitioners Act 2020 |
| VIC | Victorian Building Authority (VBA) | Essential Safety Measures, BAL (Bushfire Attack Level) requirements |
| QLD | QBCC | Wind region classifications, pool safety, Queensland Development Code (QDC) |
| WA | Building Commissioner WA | Energy efficiency variations |
| SA | Building Professional Board SA | Bushfire planning overlays |
| TAS | Consumer Building & Occupational Services | Energy efficiency addenda |
| ACT | EPSDD | Territory Plan requirements |
| NT | Dept of Infrastructure | Cyclone region D requirements |

### 2.2 Australian Standards (AS)

**Copyright constraints:** Australian Standards are copyright-protected and individually priced ($80-$500+ each). Full text cannot be embedded or reproduced.

**Legally safe content for seed data:**
- Standard numbers and official titles
- Scope descriptions (what the standard covers)
- NCC cross-references (which NCC clauses reference which AS)
- General principle summaries written in original words
- Application guidance (when/where to use each standard)

**Key standards by discipline:**

| Category | Standards | Purpose |
|----------|-----------|---------|
| **CONTRACTS & PROCUREMENT** | | |
| | AS 4000-1997 | General conditions of contract (major works, private sector) |
| | AS 2124-1992 | General conditions of contract (government/institutional) |
| | AS 4902-2000 | Design and Construct conditions of contract |
| | AS 4905-2002, AS 4949-2001 | Minor works and work order contracts |
| | AS 4901-1998, AS 2545-1993, AS 4903-2000 | Subcontract forms (for AS 4000, AS 2124, AS 4902) |
| **STRUCTURAL -- Loading** | | |
| | AS/NZS 1170.0, .1, .2, .3, .4 | Structural design actions (general, permanent/imposed, wind, snow, earthquake) |
| **STRUCTURAL -- Concrete** | | |
| | AS 3600:2018 | Concrete structures design and construction |
| | AS/NZS 4671:2019 | Steel reinforcement for concrete (rebar and mesh) |
| | AS 3610.1, .2 | Formwork for concrete (documentation, design, erection) |
| | AS 1012 (series) | Methods of testing concrete |
| **STRUCTURAL -- Steel** | | |
| | AS 4100:2020 | Steel structures design |
| | AS/NZS 5131:2016 | Structural steelwork fabrication and erection |
| | AS/NZS 1554 (series) | Structural steel welding |
| | AS/NZS 2312.1, .2 | Protective coatings for steel (paint, hot dip galvanizing) |
| | AS 4312 | Atmospheric corrosivity zones in Australia |
| **STRUCTURAL -- Timber** | | |
| | AS 1684.1, .2, .3, .4 | Residential timber-framed construction (design, non-cyclonic, cyclonic, simplified) |
| | AS 1720.1, .2 | Timber structures design methods and properties |
| | AS 5604 | Timber natural durability ratings |
| **STRUCTURAL -- Masonry & Foundations** | | |
| | AS 3700:2018 | Masonry structures design and construction |
| | AS 2159 | Piling design and installation |
| | AS 2870 | Residential slabs and footings (site classification) |
| | AS 4678 | Earth-retaining structures |
| **GEOTECHNICAL** | | |
| | AS 1726:2017 | Geotechnical site investigations (soil/rock classification) |
| | AS 1289 (series) | Methods of testing soils for engineering purposes |
| | AS 3798:2007 | Earthworks for commercial and residential developments |
| **ARCHITECTURAL -- Access & DDA** | | |
| | AS 1428.1:2021, .2, .4.1, .5 | Design for access and mobility (general, enhanced, tactile indicators, hearing) |
| **ARCHITECTURAL -- Acoustics** | | |
| | AS/NZS 2107:2016 | Recommended design sound levels for building interiors |
| | AS 3671 | Road traffic noise intrusion -- building siting and construction |
| **ARCHITECTURAL -- Glazing & Windows** | | |
| | AS 1288:2021 | Glass in buildings -- selection and installation |
| | AS 2047:2014 | Windows and external glazed doors in buildings |
| | AS 4420 (series) | Windows test methods (deflection, water, air, strength) |
| **ARCHITECTURAL -- General** | | |
| | AS 1657:2018 | Fixed platforms, walkways, stairways and ladders |
| | AS 1926.1:2024 | Swimming pool safety barriers |
| **MECHANICAL / HVAC** | | |
| | AS 1668.1 | Ventilation and air conditioning -- fire and smoke control |
| | AS 1668.2:2024 | Mechanical ventilation in buildings |
| | AS 1668.4 | Natural ventilation of buildings |
| | AS 4254.1, .2 | Ductwork for air-handling systems (flexible, rigid) |
| | AS/NZS 3823 (series) | Performance of air conditioners and heat pumps |
| | AS/NZS 5149 (series) | Refrigerating systems safety requirements |
| **ELECTRICAL -- General** | | |
| | AS/NZS 3000:2018 | Electrical installations (Wiring Rules) |
| | AS/NZS 3008.1.1 | Selection of cables for electrical installations |
| | AS/NZS 3017 | Electrical installations verification guidelines |
| | AS/NZS 61439 (series) | Low-voltage switchgear and controlgear assemblies |
| **ELECTRICAL -- Emergency & Lighting** | | |
| | AS/NZS 2293.1, .2, .3 | Emergency escape lighting and exit signs (design, inspection, construction) |
| **ELECTRICAL -- Lightning & Surge** | | |
| | AS 1768:2021 | Lightning protection |
| **ELECTRICAL -- Solar / Renewables** | | |
| | AS/NZS 5033:2021 | PV array installation and safety |
| | AS/NZS 4777.1:2024, .2 | Grid-connected inverter energy systems |
| | AS/NZS 5139 | Safety of battery systems for electrical installations |
| **HYDRAULIC / PLUMBING** | | |
| | AS/NZS 3500.0, .1, .2, .3, .4 | Plumbing and drainage (glossary, water services, sanitary, stormwater, heated water) |
| | AS/NZS 5601.1:2022 | Gas installations -- general |
| **FIRE PROTECTION -- Sprinklers** | | |
| | AS 2118.1:2017 | Automatic fire sprinkler systems -- general systems |
| | AS 2118.2 | Fire sprinkler systems -- wall-wetting sprinklers |
| | AS 2118.4 | Fire sprinkler systems -- residential (up to 4 storeys) |
| | AS 2118.5 | Home fire sprinkler systems |
| | AS 2118.6 | Combined sprinkler and hydrant systems (CMDA) |
| **FIRE PROTECTION -- Hydrants** | | |
| | AS 2419.1:2021 | Fire hydrant installations -- system design and commissioning |
| | AS 2419.2 | Fire hydrant valves |
| | AS 2419.3 | Fire brigade booster connections |
| **FIRE PROTECTION -- Detection & Alarm** | | |
| | AS 1670.1:2018 | Fire detection, warning and intercom -- system design and commissioning |
| | AS 1670.3 | Fire alarm monitoring |
| | AS 1670.4 | Sound systems and intercom for emergency purposes |
| | AS 3786:2023 | Smoke alarms (scattered light, transmitted light, ionisation) |
| **FIRE PROTECTION -- Pumps** | | |
| | AS 2941:2013 | Fixed fire protection installations -- pumpset systems |
| **FIRE PROTECTION -- Fire Resistance & Testing** | | |
| | AS 1530.1, .2, .3, .4 | Fire tests (combustibility, flammability, ignitability/heat/smoke, fire-resistance) |
| **FIRE PROTECTION -- Fire Doors & Passive** | | |
| | AS 1905.1:2015 | Fire-resistant doorsets for openings in fire-resistant walls |
| **FIRE PROTECTION -- Portable Equipment** | | |
| | AS 2444 | Portable fire extinguishers and fire blankets -- selection and location |
| **FIRE PROTECTION -- Maintenance** | | |
| | AS 1851 | Routine service of fire protection systems and equipment |
| **WATERPROOFING / ROOFING** | | |
| | AS 3740:2021 | Waterproofing of domestic wet areas |
| | AS 4654.1, .2 | Waterproofing membranes for external above-ground use (materials, design/installation) |
| | AS 4200.1, .2 | Pliable building membranes and underlays (materials, installation) |
| **FACADES & CURTAIN WALLS** | | |
| | AS 4284 | Testing of building facades |
| **LIFTS / VERTICAL TRANSPORT** | | |
| | AS 1735.1.2:2021 | Passenger and goods-passenger lifts |
| | AS 1735.2 | Escalators and moving walks |
| | AS 1735.12:2020 | Lift facilities for persons with disabilities |
| **COMMUNICATIONS / DATA** | | |
| | AS/CA S009:2020, S008:2020 | Customer cabling installation requirements and product requirements |
| | AS/NZS 3080:2013 | Generic cabling for commercial premises |
| **SECURITY** | | |
| | AS/NZS 2201.1, .2, .3, .5 | Intruder alarm systems (design, monitoring, detection, transmission) |
| | AS 4806.1, .2 | CCTV management, operation and application guidelines |
| **SUSTAINABILITY / ENERGY** | | |
| | AS/NZS 4859.1, .2 | Thermal insulation materials for buildings (criteria, design values) |
| **PAINTING / PROTECTIVE COATINGS** | | |
| | AS/NZS 2312.1, .2 | Protection of structural steel (paint coatings, hot dip galvanizing) |
| | AS 1627.4 | Metal surface preparation -- abrasive blast cleaning |
| | AS 4312 | Atmospheric corrosivity zones in Australia |
| **OCCUPATIONAL HEALTH & SAFETY** | | |
| | AS/NZS 1576 (series) | Scaffolding requirements (general, couplers, prefabricated, hanging) |
| | AS 2601:2001 | Demolition of structures |
| | AS 1418 (series) | Cranes, hoists and winches -- design and construction |
| | AS 2550 (series) | Cranes, hoists and winches -- safe use |

> **Note:** Standards with "(series)" have multiple parts (e.g., AS 1012.1, .2, etc.). The parent number is what a PM/QS typically references; part numbers are relevant to specialists. The NCC (National Construction Code) is not itself an AS standard but references many of these and is the overarching regulatory framework. Standard numbers remain stable but editions change — the app stores number and edition year separately for independent updates.

### 2.3 Sustainability Standards

| Framework | Access | Seed Content Strategy |
|-----------|--------|----------------------|
| NatHERS | Free public tools and methodology | Summarize rating methodology, star band thresholds |
| NABERS | Public rating methodology | Summarize rating levels, energy/water benchmarks |
| Green Star | Members-only detailed criteria, public rating levels | Summarize public rating descriptions, credit categories |
| BASIX (NSW) | Public calculator | Summarize target thresholds, applicable building types |

### 2.4 Contract Standards

The Australian construction industry uses several standard contract forms:

| Contract | Type | Typical Use |
|----------|------|-------------|
| AS 2124-1992 | General conditions | Government/institutional, traditional procurement |
| AS 4000-1997 | General conditions | Private sector, traditional procurement |
| AS 4902-2000 | D&C conditions | Design and construct projects |
| ABIC MW-1 | Major works | Architect-administered contracts |
| HIA contracts | Residential | Home building (mandatory in some states) |
| MBA contracts | Residential | Master Builders Association residential contracts |

---

## 3. Three-Tier Knowledge Architecture

### 3.1 Architecture Overview

The Knowledge Domain System operates across three tiers, each serving a distinct purpose and data source:

```
┌─────────────────────────────────────────────────────────────┐
│                    QUERY-TIME ASSEMBLY                        │
│     Tier 3: Dynamic / AI-Synthesized Knowledge               │
│     Claude + Tier 1 + Tier 2 + Project Context              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │  Tier 1: Baked-In    │  │  Tier 2: Organization-       │ │
│  │  Reference Knowledge │  │  Uploaded Libraries          │ │
│  │                      │  │                              │ │
│  │  - NCC clause index  │  │  - Company procedures        │ │
│  │  - AS standard       │  │  - Contract templates        │ │
│  │    catalog            │  │  - Past project close-outs  │ │
│  │  - State variations  │  │  - Trade specifications      │ │
│  │  - Contract type     │  │  - Design guidelines         │ │
│  │    comparisons        │  │  - Quality standards        │ │
│  │  - Building class    │  │                              │ │
│  │    definitions        │  │  (Existing RAG pipeline     │ │
│  │  - Best-practice     │  │   with domain tags added)    │ │
│  │    guides             │  │                              │ │
│  └──────────────────────┘  └──────────────────────────────┘ │
│                                                               │
│                    Vector Database (pgvector)                 │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Tier 1: Baked-In Reference Knowledge (Seed Data)

Pre-authored knowledge chunks that ship with the platform. Every organization gets these automatically. Content is written in original language with references to authoritative sources.

**Included:**
- NCC clause reference index (numbers, titles, descriptions in original words)
- AS standard catalog (numbers, titles, scope descriptions)
- State/territory variation summaries per jurisdiction
- Contract type reference (AS 2124, AS 4000, ABIC, HIA comparisons)
- Common regulatory pathways (DA, CC, OC process)
- Building class definitions (Class 1a through Class 10c)
- Construction stage checklists and milestone guidance
- Cost management principles (contingency, variations, progress claims)
- Procurement and tendering best practices
- Program and scheduling guidance

**Explicitly NOT included:**
- Full text of any standard or code
- Deemed-to-Satisfy provision tables
- Detailed engineering requirements or calculation methods
- Proprietary rating tool criteria

### 3.3 Tier 2: Organization-Uploaded Knowledge Libraries

Organization-specific documents processed through the existing RAG pipeline, now enhanced with domain classification. Organizations upload their own:

- Company-specific contract templates and standard clauses
- Internal procedures and quality management documents
- Past project close-out reports and lessons learned
- Trade-specific specifications and design guidelines
- Preferred supplier lists and prequalification criteria

These documents flow through the existing document processing worker (parse -> chunk -> embed -> store) but are tagged with domain metadata for targeted retrieval.

### 3.4 Tier 3: Dynamic / AI-Synthesized Knowledge

Assembled at query time by combining Tier 1 seed data, Tier 2 organization documents, project-specific context, and Claude's training knowledge. The key insight is that Claude already has substantial knowledge of Australian building codes and construction practices from its training data. What it needs is the **citation pathway** -- structured references that let it ground its answers in verifiable sources rather than relying on parametric knowledge alone.

The Context Orchestrator (Pillar 2) handles the assembly of Tier 3 knowledge at query time, pulling from domain-tagged retrieval results and formatting them for the AI prompt.

---

## 4. Domain Taxonomy and Tag System

### 4.1 Pre-Built Domain Definitions

Ten pre-built knowledge domains, each with a domain type, set of tags, and description:

| # | Domain Name | Domain Type | Tags | Description |
|---|------------|-------------|------|-------------|
| 1 | NCC Reference Guide | `reference` | `ncc`, `regulatory` | National Construction Code clause index, building classifications, performance requirements |
| 2 | AS Standards Reference | `reference` | `as-standards`, `regulatory` | Australian Standards catalog, scope descriptions, NCC cross-references |
| 3 | Residential Construction Guide | `best_practices` | `residential`, `construction` | Best practices for Class 1/10 residential projects |
| 4 | Multi-Residential/Apartments Guide | `best_practices` | `residential`, `commercial`, `apartments` | Best practices for Class 2-4 multi-residential projects |
| 5 | Commercial Construction Guide | `best_practices` | `commercial`, `construction` | Best practices for Class 5-9 commercial and institutional projects |
| 6 | Cost Management Principles | `best_practices` | `cost-management`, `budgeting`, `variations` | Cost planning, contingency, progress claims, forecast management |
| 7 | Procurement & Tendering Guide | `best_practices` | `procurement`, `contracts`, `tendering` | Tender process, evaluation criteria, RFT preparation |
| 8 | Contract Administration Guide | `best_practices` | `contracts`, `as2124`, `as4000`, `variations`, `eot`, `defects` | Contract management, variations, extensions of time, defect liability |
| 9 | Program & Scheduling Guide | `best_practices` | `programming`, `milestones`, `critical-path` | Construction programming, milestone tracking, delay analysis |
| 10 | Remediation & Due Diligence Guide | `best_practices` | `remediation`, `due-diligence`, `environmental` | Site investigation, contamination assessment, remediation action plans |

### 4.2 Domain Type Enum

```typescript
export const DOMAIN_TYPES = [
  'reference',         // Regulatory and standards references
  'regulatory',        // Jurisdiction-specific regulatory content
  'best_practices',    // Industry best-practice guidance
  'templates',         // Document and process templates
  'project_history',   // Past project lessons learned
  'custom',            // User-defined custom domains
] as const;

