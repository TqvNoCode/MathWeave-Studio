<div align="center">

[English](README.md) | [Tiếng Việt](README.vi.md)

<br />
<br />

<img src="assets/icon.svg" width="96" height="96" alt="MathWeave Studio Logo" />

# MathWeave Studio

**An interactive mathematical workspace for pedagogical step-by-step solutions, independent symbolic verification, and 2D/3D visualization.**

*MathWeave Studio is designed to help students and researchers understand mathematical reasoning and transformation rules, rather than treating computer algebra as a black-box answer engine.*

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![Status: MVP v0.1.0](https://img.shields.io/badge/Status-MVP%20v0.1.0-orange.svg)](pyproject.toml)

</div>

---

## Overview

Most mathematical software outputs only a final answer, leaving learners unsure of how a solution was derived or whether intermediate steps are sound.

MathWeave Studio bridges this gap by combining:
- **Symbolic Computation:** Exact mathematical computation powered by SymPy.
- **Pedagogical Derivation Engine:** Step-by-step decomposition of standard calculus rules (Power, Sum, Product, Quotient, Chain, Trig rules) with expandable substeps.
- **Dual-Layer Independent Verification:** Every solution is independently cross-checked against reference symbolic invariants and multi-point numerical probing.
- **Interactive Visualization:** 2D function plotting with automatic singularity/asymptote detection, standardized 3D surface visualization, and variation tables (*bảng biến thiên*).

> **Note on Versioning:** MathWeave Studio is currently in active MVP development (`v0.1.0`). Pushing commits to GitHub does not publish a new release version; a GitHub Release and matching Git tag must be created for release-tracking badges to update automatically.

---

<!-- DEMO / SCREENSHOT PLACEHOLDER: A representative application screenshot or demo recording will be placed here once committed to the repository assets. -->

## Features

### Calculus
- **Derivatives:** First-order and higher-order derivatives ($f^{(n)}(x)$ up to order 10) and partial derivatives ($\frac{\partial f}{\partial x}$, $\frac{\partial f}{\partial y}$).
- **Integrals:** Indefinite integration with rule breakdown and integration constant $+ C$; definite integrals over $[a, b]$ via the Fundamental Theorem of Calculus.
- **Limits:** Two-sided and one-sided limits ($\lim_{x \to a^{\pm}}$) at finite points and infinities ($\pm\infty$).
- **Geometry & Multivariable:** Arc length, surface area, surfaces/solids of revolution, line and surface integrals, and triple integrals (Cartesian, cylindrical, spherical).

### Linear Algebra
- **Determinants:** $2 \times 2$ formula and Laplace expansion for higher-order matrices.
- **Matrix Inverses ($A^{-1}$):** Invertibility checks ($\det A \ne 0$) and adjugate matrix calculation.
- **Echelon Forms:** Gaussian elimination (REF) and Gauss-Jordan elimination (RREF) with elementary row operations.
- **Matrix Operations:** Addition, subtraction, multiplication ($A \times B$), and transpose ($A^T$).
- **Linear Systems ($Ax = b$):** Augmented matrix $[A | b]$ solving with complete solution classification.

### Verification & Rationale
- **Dual-Layer Auditing:** Every result displays an audit badge (*Verified* via symbolic invariant or *Numerical Probe* sampling with error $< 10^{-9}$).
- **Domain Restrictions ($\mathcal{D}$):** Automatic detection of non-zero denominator conditions, non-negative radical constraints, and trigonometric singularities.

### Visualization
- **2D Plotting (Plotly):** Interactive graphs with zoom, pan, and automatic pole detection to prevent invalid line connections across vertical asymptotes.
- **3D Visualization:** Isometric 3D surfaces and space curves with RGB coordinate axes (X=Red, Y=Green, Z=Blue).
- **Variation Tables:** Academic variation tables showing domain, critical points, poles (double bar `||`), derivative signs, and monotonicity arrows.

---

## Installation

MathWeave Studio is primarily developed and tested on **Arch Linux**.

### Quick Start (Arch Linux via uv)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/TqvNoCode/MathWeave-Studio.git
   cd MathWeave-Studio
   ```

2. **Synchronize dependencies:**
   ```bash
   uv sync
   ```

3. **Launch the application:**
   ```bash
   uv run run.py --browser
   ```

Open your browser at: **[http://localhost:8080](http://localhost:8080)**

For complete Arch Linux instructions—including future AUR installation placeholders, system dependencies, running with standard virtual environments, and uninstallation—see the [Arch Linux Installation Guide](docs/INSTALL_ARCH.md).

---

## Documentation

- 🐧 **[Arch Linux Installation Guide (INSTALL_ARCH.md)](docs/INSTALL_ARCH.md):** Detailed guide for Arch Linux users, yay/AUR status, source setup, and clean uninstallation.
- 📖 **[User Guide (USER_GUIDE.md)](docs/USER_GUIDE.md):** Complete practical guide covering the 5-step workflow, representative examples, input syntax, and troubleshooting.

---

## Development & Testing

MathWeave Studio maintains an automated test suite enforcing Clean Architecture boundary isolation, solver mathematical validity, and UI stability:

```bash
# Run all 206 automated tests
uv run pytest
```

All 206 tests pass with 100% success rate.

---

## License & Author

- **License:** GNU General Public License v3.0 ([GPL-3.0](LICENSE)).
- **Author:** TQV (`TqvNoCode` — `92263302+TqvNoCode@users.noreply.github.com`)
- **Copyright:** `© 2026 by TQV`
