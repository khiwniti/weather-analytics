# AI Weather Analytics Platform

## What This Is

An AI-powered weather analytics and simulation platform built on the NVIDIA developer stack. It combines physics-based numerical weather prediction (NWP) with AI-accelerated parameterization and stunning 3D terrain visualization. The platform serves two primary user groups: meteorologists requiring deep analytical capabilities for weather forecasting and decision support, and general users needing intuitive weather monitoring and visualization.

## Core Value

**Scientifically accurate weather visualization that enables actionable decisions.** Every pixel must reflect physics-consistent model outputs, not artistic interpretation. AI accelerates but never replaces physics fundamentals.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Real-time weather data ingestion from multiple sources (NWP models, radar, satellite, ground observations)
- [ ] GPU-accelerated data processing via NVIDIA RAPIDS (cuDF, cuSpatial)
- [ ] NVIDIA Clara Holoscan integration for sensor fusion and quality control
- [ ] Physics-constrained AI parameterization for weather models (Earth-2, Modulus)
- [ ] NVIDIA Omniverse-based 3D terrain visualization with RTX path tracing
- [ ] Volumetric weather rendering (clouds, precipitation, wind, lightning)
- [ ] High-resolution terrain streaming from USGS 3DEP/Copernicus DEM
- [ ] Dual interface: scientist view with diagnostics and public view with intuitive visualization
- [ ] Impact forecasting and risk hotspot analytics
- [ ] Explainable AI (XAI) for forecast reasoning

### Out of Scope

- Pure AI weather generators without physics constraints — violates conservation laws
- Custom NWP solver development — use WRF/MPAS as physics core
- Mobile application — focus on desktop/cloud first
- Historical climate analysis (>14 days) — relies on different Earth System Models

## Context

### Technical Background

This platform follows a battle-tested architecture documented in `nvidia_nemetron_respons.md`, which provides comprehensive implementation details for:

- **Layer 0**: Terrain and observational data foundation (RAPIDS cuSpatial, Clara Holoscan)
- **Layer 1**: Physics core acceleration (NVIDIA HPC SDK, Earth-2, Modulus)
- **Layer 2**: Nowcasting and uncertainty quantification (Video Diffusion Models, cuML)
- **Layer 3**: 3D visualization (Omniverse, RTX, Falcor, PhysX, Flow)
- **Layer 4**: Analytics and alerts (cuML, cuGraph, Morpheus, NeMo)

### Key Architecture Principles

1. **Physics core remains inviolate**: NWP dynamic core (Navier-Stokes solver) stays physics-based
2. **AI replaces parameterizations only**: Radiation, microphysics, PBL replaced with physics-constrained surrogates
3. **Visualization = truth**: Omniverse USD preserves exact model coordinates
4. **Conservation laws enforced**: Modulus PINNs embed mass/energy constraints

### NVIDIA SDK Integration

| Layer | NVIDIA Tool | Purpose |
|-------|-------------|---------|
| Data Ingestion | Clara Holoscan, RAPIDS | Real-time sensor fusion, GPU-accelerated ETL |
| Physics Acceleration | Earth-2, Modulus, HPC SDK | Replace physics params, accelerate WRF core |
| Nowcasting | Video Diffusion Models | Generate photorealistic 0-1h forecast frames |
| Rendering | Omniverse, RTX, IndeX, Flow | Physically accurate 3D terrain + weather visualization |
| Analytics | RAPIDS cuML/cuGraph, Morpheus | GPU-ML, anomaly detection, AI model serving |
| Transitions | DLSS 3.5, Omniverse Streaming | AI-frame interpolation, predictive streaming |

## Constraints

- **Compute**: NVIDIA LaunchPad free tier initially, scale to DGX Cloud or AWS G5/G6 instances
- **Integration**: Use NVIDIA APIs and pre-built connectors where available (not raw SDK)
- **Terrain Resolution**: High-res DEM (USGS 3DEP LiDAR where available, Copernicus 30m fallback)
- **Weather Sources**: All sources integrated (GFS/ECMWF NWP, NEXRAD radar, GOES satellite, ground obs)
- **Visualization**: Complete weather phenomena (precipitation, wind, lightning, fog)
- **Budget**: Free tier during development, cloud budget for production

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full NVIDIA stack integration | Leverages GPU-accelerated everything, optimal for weather AI | — Pending |
| WRF/MPAS as physics core | Cannot replace Navier-Stokes solver with AI (violates conservation) | — Pending |
| Omniverse for visualization | USD preserves model coordinates, RTX path tracing for realism | — Pending |
| NVIDIA API integration over raw SDK | Faster integration, pre-built connectors available | — Pending |
| Free LaunchPad tier first | Validate architecture before cloud spend | — Pending |
| Dual user experience | Meteorologists need diagnostics, public needs simplicity | — Pending |

---
*Last updated: 2025-03-19 after initialization*
