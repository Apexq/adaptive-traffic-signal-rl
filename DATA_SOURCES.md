# DATA_SOURCES.md — Benchmark Network & Dataset Citations

This repository evaluates adaptive traffic signal controllers using the official **RESCO (Reinforcement Learning Benchmarks for Traffic Signal Control)** benchmark suite, introduced at **NeurIPS 2021** (Track on Datasets and Benchmarks), and the **TAPASCologne 0.0.3** calibrated realistic urban mobility dataset for Eclipse SUMO.

---

## 1. Primary Evaluation Network: RESCO Cologne-3 (`nets/cologne3/`)

The primary multi-intersection arterial corridor scenario evaluated in this project is located in **Cologne (Köln-Lindenthal), Germany**, along **Dürener Straße**. It comprises three consecutive signalized intersections operating under morning peak-hour demand (`07:00–08:00 AM`, simulation seconds `25200` to `28800`):

1. **West Junction (Node 359566 / `GS_cluster_2415878664_254486231_359566_359576`):**
   - Intersection: Dürener Straße & Lindenthalgürtel / Stadtwaldgürtel
   - Phases: 4 green phases (`Phases 0, 2, 4, 6`), including dedicated protected left-turn phases and bidirectional tramway tracks.
2. **Center Junction (Node 360086):**
   - Intersection: Dürener Straße & Theresienstraße / Klosterstraße
   - Phases: 4 green phases (`Phases 0, 2, 4, 6`) connecting collector streets to the arterial.
3. **East Junction (Node 360082):**
   - Intersection: Dürener Straße & Geibelstraße / Herbert-Lewin-Straße
   - Phases: 3 green phases (`Phases 0, 2, 4`) serving transit access to the University of Cologne Hospital (*Uniklinik Köln*).

---

## 2. Secondary Network: RESCO Cologne-1 (`nets/cologne1/`)

The single-intersection benchmark scenario models the major arterial intersection at **Dürener Straße & Universitätsstraße** (Node `357187`), featuring 4 green phases with dedicated protected turn pockets.

---

## 3. Academic Citations

If you use or reference this codebase, please cite the underlying benchmark datasets:

```bibtex
@inproceedings{ault2021reinforcement,
  title={Reinforcement Learning Benchmarks for Traffic Signal Control},
  author={Ault, James and Sharon, Guni},
  booktitle={Thirty-fifth Conference on Neural Information Processing Systems (NeurIPS) Datasets and Benchmarks Track},
  year={2021},
  url={https://openreview.net/forum?id=tB6zbR8fnnn}
}

@inproceedings{uppoor2014large,
  title={Large-scale urban mobility simulations for vehicular networks: The TAPASCologne dataset},
  author={Uppoor, Sandesh and Trullols-Cruces, Oscar and Fiore, Marco and Barcelo, Jose Maria},
  booktitle={IEEE Transactions on Vehicular Technology},
  volume={63},
  number={2},
  pages={533--547},
  year={2014},
  publisher={IEEE}
}
```

---

## 4. License & Usage Terms

- The TAPASCologne simulation scenario files are distributed under the **Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported (CC BY-NC-SA 3.0)** license.
- Network topologies and route definitions are preserved in their original NeurIPS 2021 RESCO structure to ensure scientific reproducibility.
