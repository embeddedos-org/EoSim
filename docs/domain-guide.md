# Domain Guide — Adding New Industry Domains

## Overview

EoSim supports 40 industry domains. Each domain includes:

1. **Domain Profile** — standards, safety levels, typical architectures
2. **Schema Entry** — validation in `VALID_DOMAINS`
3. **Simulator(s)** — domain-specific simulation logic
4. **Product Templates** — pre-configured products
5. **GUI Renderer** — 3D visualization
6. **Platform Definitions** — target hardware definitions

## Current Domains (40)

| Domain | Standards | Safety |
|--------|-----------|--------|
| automotive | ISO 26262, AUTOSAR | ASIL-A to D |
| aerospace | DO-178C, ARINC 653 | DAL-A to E |
| medical | IEC 62304, FDA | Class A/B/C |
| industrial | IEC 61508 | SIL-1 to 4 |
| nuclear | IEC 61513, IEEE 603 | SIL-3/4 |
| railway | EN 50128/50129, ETCS | SIL-3/4 |
| defense | MIL-STD-810/461 | SIL-3/4 |
| energy | IEC 61850 | SIL-2/3 |
| telecom | 3GPP, O-RAN | — |
| iot | MQTT, CoAP | — |
| consumer | Bluetooth, Matter | — |
| robotics | ROS 2, ISO 10218 | PLd/e |
| agriculture | ISO 11783 (ISOBUS) | PLa/b |
| maritime | IMO SOLAS, NMEA | SIL-1/2 |
| mining | IEC 60079, MSHA | SIL-2/3 |
| construction | ISO 15998, EN 13849 | PLc/d/e |
| retail | PCI DSS, EMV | — |
| education | IEEE P2841 | — |
| sports | ANT+, BLE | — |
| smart-city | FIWARE, oneM2M | SIL-1 |
| space | ECSS, CCSDS | Cat-1/2/3 |
| quantum | IEEE P7131 | — |
| hvac | ASHRAE 135, BACnet | SIL-1 |
| printing | ISO/ASTM 52900 | — |
| elevator | EN 81-20, ISO 8100 | SIL-3 |
| traffic | NTCIP, ETSI ITS | SIL-1/2 |
| water | EPA SCADA, AWWA | SIL-1/2 |
| oil-gas | API 1164, ISA-95 | SIL-2/3 |
| forestry | ISO 11850 | PLb/c |
| fisheries | IMO SOLAS | — |
| logistics | GS1, VDA 5050 | PLd |
| cybersecurity | FIPS 140-3, CC | EAL4-6 |
| ar-vr | OpenXR, Khronos | — |
| aerodynamics | NASA CFD, AIAA | — |
| physiology | HL7 FHIR | Class I-III |
| finance | FIX, ISO 20022 | Critical/High |
| weather | WMO, GRIB2 | — |
| gaming | PhysX, Vulkan | — |
| photonics | IEEE 802.3, ITU-T | — |
| neuromorphic | IEEE 2801 | — |

## Adding a New Domain

### Step 1: Schema (`eosim/core/schema.py`)
Add the domain name to `VALID_DOMAINS`.

### Step 2: Domain Profile (`eosim/core/domains.py`)
Add a `DomainProfile` entry to `DOMAIN_CATALOG`.

### Step 3: Simulator (`eosim/engine/native/simulators/`)
Create a new simulator file. See [Simulator Guide](simulator-guide.md).

### Step 4: Product Templates (`eosim/gui/product_templates.py`)
Add at least one product template for the domain.

### Step 5: Platform Definition (`platforms/`)
Create a platform YAML for the domain.

### Step 6: GUI Renderer (`eosim/gui/renderers/`)
Create a domain-specific 3D renderer.

### Step 7: Tests
Add tests covering the new simulator, domain profile, and products.
