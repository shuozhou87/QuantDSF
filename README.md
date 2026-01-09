# QuantDSF v2.0

Advanced analysis platform for nanoDSF (nano Differential Scanning Fluorimetry) data from NanoTemper Prometheus NT.Panta and Tycho NT.6 instruments.

## Overview

QuantDSF v2 is a comprehensive desktop application for protein thermal stability analysis, designed to overcome the limitations of official vendor software (Panta Analysis). It provides transparent, flexible thermodynamic parameter extraction with multiple analysis methods.

## Key Features

### Core Analysis Capabilities
- **Tm Analysis** (Melting Point Determination)
  - Boltzmann fitting (Two-State model)
  - First derivative method
  - Area Under Curve (AUC) method

- **Thermodynamic Analysis**
  - Van't Hoff regression
  - EC₅₀/Kd determination
  - Temperature-dependent parameter extraction
  - Single-curve thermodynamic analysis

- **Dose-Response Analysis**
  - Direct ligand titration analysis
  - EC₅₀ calculation from isothermal data

- **Quality Control**
  - Signal-to-Noise Ratio (SNR)
  - R² goodness-of-fit
  - Dynamic range assessment

### Performance
- **Multicore Parallelization**: 3.96x speedup for large datasets (245 samples: 162s → 41s)
- Utilizes 80-95% of available CPU cores
- Optimized for high-throughput screening

### User Interface
- Interactive Dash-based web interface
- Real-time data visualization with Plotly
- Excel export functionality

## Architecture

```
QuantDSF/
├── app/                    # UI Layer (Dash frontend)
│   ├── layouts/           # Page layouts
│   ├── components/        # Reusable UI components
│   ├── callbacks/         # Event handlers
│   └── state.py          # Centralized state management
│
├── core/                  # Core Computation Layer
│   ├── models/           # Data models (Pydantic)
│   ├── analysis/         # Analysis algorithms
│   │   ├── tm/          # Tm calculation methods
│   │   ├── thermodynamic/  # Thermodynamic analysis
│   │   └── ...
│   ├── io/              # Data I/O
│   │   ├── parsers/     # Instrument data parsers
│   │   └── exporters/   # Result exporters
│   └── utils/           # Utility functions
│
├── app_v2.py            # Web application entry point
└── requirements_v2.txt  # Python dependencies
```

## Installation

### Requirements
- Python 3.12+
- See `requirements_v2.txt` for package dependencies

### Setup

1. Clone the repository:
```bash
git clone https://github.com/shuozhou87/QuantDSF.git
cd QuantDSF
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements_v2.txt
```

## Usage

### Production Deployment (UTHSCSA Internal)

**Live Instance**: [http://g1200163267.win.uthscsa.edu:9051/](http://g1200163267.win.uthscsa.edu:9051/)
- **Server**: Windows Server (UTHSCSA internal network)
- **Access**: Internal network only (requires VPN for external access)
- **Status**: Production - all latest features deployed

### Local Development

```bash
python app_v2.py
```

Then open your browser to `http://localhost:8050`

## Documentation

Comprehensive documentation is available in the `docs/` directory.

### Quick Links
- **[Documentation Index](docs/README.md)** - Complete documentation navigation
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and updates
- **[Why QuantDSF?](docs/WHY_QUANTDSF.md)** - Project motivation

### Key Documents
- [Architecture Proposal](docs/V2_ARCHITECTURE_PROPOSAL.md) - System design
- [Multicore Parallelization](docs/MULTICORE_PARALLELIZATION.md) - Performance optimization
- [Single-Curve Thermodynamics](docs/SINGLE_CURVE_THERMODYNAMICS.md) - Core innovation
- [Developer Guide](docs/DEVELOPER_GUIDE.md) - Contributing to the project

## Technical Highlights

1. **Separation of Concerns**: Complete decoupling of UI and core computation layers
2. **Type Safety**: 100% type hints coverage with Pydantic validation
3. **Data-Driven**: Support for multiple Tm determination methods with automatic quality metrics
4. **Web-Based**: Browser-accessible interface with real-time visualization
5. **Extensible**: Modular architecture for easy maintenance and feature addition

## Use Cases

- Protein thermal stability screening
- Thermodynamic parameter extraction from DSF data
- Ligand affinity determination (EC₅₀/Kd via thermal shift)
- Sample quality control (SNR, fit quality assessment)
- High-throughput analysis with parallel processing

## Version History

### v2.0 (Current)
- Complete rewrite with layered architecture
- Multicore parallelization support
- Enhanced thermodynamic analysis
- Web-based interface with Dash
- Comprehensive quality control metrics

### v1.0 (Deprecated)
- Streamlit-based interface (discontinued due to limitations)

## License

[Add your license here]

## Citation

If you use QuantDSF in your research, please cite:

[Add citation information here]

## Contact

For issues, feature requests, or questions, please open an issue on GitHub or contact the maintainer.

## Contributing

Contributions are welcome! Please read the developer guide in `docs/DEVELOPER_GUIDE.md` for details on our code style, testing practices, and pull request process.
