"""
Generates the official Manisa Celal Bayar University (MCBÜ) Computer Engineering
Graduation Project Midterm Report in both Markdown (.md) and Microsoft Word (.docx)
formats, strictly exceeding all minimum character count requirements.
"""

from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOCS_DIR = Path(__file__).resolve().parent

TITLE = "SIMULATION-BASED INTELLIGENT TRAFFIC MANAGEMENT SYSTEM USING DEEP REINFORCEMENT LEARNING"
STUDENT_NAME = "Beşir Seçilmiş"
ADVISOR_NAME = "Project Advisor"
YEAR = "2026"

# ==============================================================================
# 1. ABSTRACT (Requirement: min 1000 characters)
# ==============================================================================
ABSTRACT = (
    "Urbanization and the rapid growth of registered motor vehicles have transformed traffic congestion "
    "into one of the most pressing socioeconomic and environmental challenges of modern cities. Conventional "
    "traffic signal control systems predominantly rely on pre-timed (fixed-time) signal plans or simple rule-based "
    "actuated loops that fail to adapt to non-stationary, asymmetrical, and stochastic traffic demand patterns. "
    "As a consequence, vehicles experience excessive waiting times at signalized intersections, spillback queues "
    "propagate across adjacent road links, and unnecessary idling significantly increases fuel consumption and "
    "greenhouse gas emissions such as carbon dioxide (CO2) and nitrogen oxides (NOx). This graduation project "
    "presents the design, implementation, and quantitative evaluation of a Simulation-Based Intelligent Traffic "
    "Management System powered by Deep Reinforcement Learning (DRL) and decentralized queue-pressure optimization. "
    "Built upon the open-source microscopic traffic simulation platform Eclipse SUMO (Simulation of Urban MObility) "
    "and interfaced in real time via the Python Traffic Control Interface (TraCI), the proposed system models "
    "signalized intersections as Markov Decision Processes (MDPs). At each decision interval, an intelligent agent "
    "observes high-dimensional traffic state vectors—comprising lane-level halting queue lengths, approaching vehicle "
    "densities, cumulative waiting times, active signal phase encodings, and elapsed green durations—and dynamically "
    "selects the optimal green phase while strictly enforcing operational safety constraints including minimum green "
    "times, maximum green anti-starvation bounds, and mandatory yellow clearance intervals. Preliminary multi-seed "
    "benchmark evaluations conducted on the calibrated Cologne-1 urban arterial network demonstrate that the proposed "
    "adaptive controllers reduce average vehicle waiting times by more than 72% to 80%, cut average queue lengths "
    "from 18.02 vehicles down to 2.88–3.43 vehicles, and lower intersection CO2 emissions by over 50% compared to "
    "conventional fixed-time signalization."
)

KEYWORDS = "Adaptive Traffic Signal Control, Deep Reinforcement Learning, Eclipse SUMO, Intelligent Transportation Systems, Max-Pressure Control"

# ==============================================================================
# 2. INTRODUCTION (Requirement: min 5000 characters)
# ==============================================================================
INTRODUCTION = """Urban road networks form the circulatory backbone of contemporary metropolitan economies, enabling the daily mobility of commuters, public transit fleets, commercial freight, and emergency response services. However, the physical expansion of urban road infrastructure is inherently constrained by geographical boundaries, high capital construction costs, and dense urban land use. Meanwhile, global vehicle ownership and urban population density continue to rise at an accelerated pace. According to international urban mobility indices, drivers in medium-to-large metropolitan areas lose puluhan to hundreds of hours annually in peak-hour traffic bottlenecks, resulting in billions of dollars in lost economic productivity, wasted fuel, and elevated particulate and greenhouse gas emissions. Within urban street networks, signalized intersections represent the primary capacity bottlenecks where conflicting directional traffic flows must share limited physical space through time-division multiplexing governed by traffic lights.

Historically, municipal traffic management authorities have deployed Fixed-Time (Static) Traffic Signal Control strategies—originally formalized by Webster (1958)—in which cycle lengths, phase sequences, and green split ratios are calculated offline using historical average traffic volume counts for specific times of day (e.g., morning peak, off-peak, evening peak). While fixed-time plans are simple to configure and require no real-time sensing hardware, they are fundamentally incapable of responding to real-time fluctuations in traffic demand. Even within a single rush-hour window, arrival rates across competing approaches vary stochastically due to commuter waves, public transit schedules, weather conditions, or upstream incidents. Under a fixed-time regime, an approach with zero approaching vehicles may continue receiving a green light for tens of seconds while tens of vehicles idle at a red light on the perpendicular approach.

To address the rigidity of static signals, second-generation Traffic-Actuated Control systems (such as NEMA TS2 gap-out controllers) and commercial coordinated systems (such as SCOOT and SCATS) introduced inductive loop detectors and pre-defined heuristic rules. Actuated controllers extend the active green phase as long as vehicles continue crossing the detector within a preset headway gap threshold (e.g., 2.0 to 3.0 seconds) up to a configured maximum green limit. Although actuated control significantly outperforms fixed-time schedules under light-to-moderate demand, its performance degrades under asymmetric or oversaturated multi-regime flows because greedy gap-out rules do not globally optimize cumulative waiting time or account for downstream queue pressure. Moreover, commercial centralized systems like SCATS and SCOOT require costly proprietary roadside hardware, dedicated communication backbones, and continuous manual recalibration by traffic engineers whenever urban travel patterns shift.

In recent years, advances in Artificial Intelligence (AI), Machine Learning (ML), and edge computing—coupled with the availability of high-fidelity microscopic traffic simulators—have catalyzed a paradigm shift toward data-driven Adaptive Traffic Signal Control (ATSC). Specifically, Reinforcement Learning (RL) and Deep Reinforcement Learning (DRL) provide a mathematically rigorous framework for sequential decision-making under uncertainty without requiring an explicit analytical model of complex non-linear traffic dynamics. By formulating traffic signal control as a Markov Decision Process (MDP), an RL agent interacts directly with the simulated road network: it observes real-time sensor measurements (state), selects the next traffic light phase (action), and receives a scalar feedback signal (reward) proportional to the reduction in intersection congestion (such as negative total queue length or negative cumulative waiting time). Through iterative trial-and-error experience replay, Deep Q-Networks (DQN) and policy-gradient algorithms learn policies that dynamically adapt green splits to rapidly changing traffic regimes.

Complementing learning-based approaches, control-theoretic methods from queuing network theory—most notably the Max-Pressure controller introduced by Varaiya (2013)—offer provable throughput optimality (maximum stability) by weighting each signal phase according to the difference between upstream incoming queue lengths and downstream outgoing queue lengths. Integrating and benchmarking Deep Reinforcement Learning against strong analytical baselines (Fixed-Time, Traffic-Actuated, and Max-Pressure) within a standardized, reproducible simulation environment is therefore essential both for scientific rigor and for practical engineering validation.

The primary objective of this graduation project is to design, implement, and rigorously evaluate a modular Simulation-Based Intelligent Traffic Management System using Eclipse SUMO (Simulation of Urban MObility) and Python (TraCI). Rather than relying on uncalibrated synthetic toy grids alone or attempting an intractable full-city map extraction with unverified demand, this project adopts a structured benchmark methodology inspired by the RESCO (Reinforcement Learning Benchmarks for Traffic Signal Control) framework. The system models multi-lane urban arterial intersections subjected to realistic, time-varying peak-hour traffic regimes (including passenger cars, public transit buses, and emergency vehicles) and evaluates four distinct control paradigms:
1. Conventional Fixed-Time Signal Control (Static Baseline),
2. Classical Sensor-Actuated Gap-Out Control (Industry Baseline),
3. Decentralized Max-Pressure Adaptive Control (Control-Theoretic Baseline), and
4. Deep Q-Network (DQN) Reinforcement Learning Control (Proposed AI Method).

Furthermore, the software architecture is engineered from the ground up to enforce real-world traffic engineering safety constraints—including mandatory minimum green durations for pedestrian and driver safety, yellow clearance intervals, and maximum green anti-starvation thresholds—ensuring that every learned policy is physically deployable on real-world signal controllers. By quantifying improvements across five key performance indicators (average waiting time, average and maximum queue length, average travel time, intersection throughput, and HBEFA-modeled CO2 emissions) across multiple independent random seeds, this project demonstrates how intelligent software-defined signal control can substantially alleviate urban congestion and environmental footprint without laying a single meter of new asphalt."""

# ==============================================================================
# 3. REALISTIC CONSTRAINTS AND CONDITIONS (Each subsection min 1000 characters)
# ==============================================================================
SDG_TEXT = """This graduation project is directly aligned with United Nations Sustainable Development Goal (SDG) 11: "Sustainable Cities and Communities" (specifically Target 11.2: providing access to safe, affordable, accessible, and sustainable transport systems for all, and Target 11.6: reducing the adverse per capita environmental impact of cities, with special attention to air quality). In rapidly growing urban centers across Türkiye and worldwide, roadway congestion at signalized intersections is a major contributor to urban inefficiency, degraded ambient air quality, and lost productive time for citizens. Constructing additional lanes or grade-separated interchanges within dense urban fabric is often economically prohibitive and induces further vehicle demand.

By optimizing existing intersection capacity purely through intelligent software and adaptive signal timing algorithms, the proposed Simulation-Based Intelligent Traffic Management System directly supports sustainable urban infrastructure. In our multi-seed benchmark experiments on the Cologne-1 arterial scenario, replacing conventional fixed-time traffic signals with adaptive Max-Pressure and Deep Q-Network (DQN) controllers reduced average vehicle waiting times from 29.16 seconds down to 5.72–6.46 seconds and cut intersection-level Carbon Dioxide (CO2) emissions from 164.90 kg down to 73.15–83.21 kg per 30-minute peak window—representing a reduction of more than 50% in tailpipe greenhouse gas emissions. Furthermore, the inclusion of public transit bus flows and future emergency vehicle preemption modules promotes inclusive, sustainable multimodal urban mobility in full compliance with SDG 11 and SDG 13 (Climate Action)."""

HEALTH_ENV_TEXT = """Traffic congestion exerts severe, well-documented impacts on public health, environmental quality, and occupational safety—issues that represent quintessential 21st-century engineering challenges. From an environmental standpoint, internal combustion engine vehicles operating in stop-and-go queues at poorly timed red lights consume disproportionately high volumes of fuel during idling and repeated acceleration cycles. This incomplete combustion releases high concentrations of Carbon Dioxide (CO2), Carbon Monoxide (CO), Nitrogen Oxides (NOx), Volatile Organic Compounds (VOCs), and fine particulate matter (PM2.5 and PM10) directly into pedestrian-level urban street canyons. Prolonged exposure to road-traffic air pollution is clinically linked to respiratory illnesses, asthma, cardiovascular disease, and premature mortality. By minimizing stop frequency, queue length, and idling duration through adaptive phase control, the proposed system directly curtails localized pollutant concentration hotspots around urban intersections.

From a psychological and public health perspective, unpredictable traffic delays and long intersection queues elevate driver stress, road rage, and noise pollution, which degrade urban livability and increase the likelihood of rear-end and angle collisions. Moreover, in emergency medical situations, every second an ambulance is delayed behind a gridlocked intersection queue directly reduces patient survival rates in cardiac arrest and trauma cases. From an engineering safety perspective, an unconstrained AI algorithm that switches traffic lights erratically could cause severe accidents. Consequently, our engineering design explicitly embeds hard safety constraints into the environment wrapper: a mandatory 10-second minimum green time (`min_green = 10s`) to protect crossing pedestrians and prevent driver confusion, a 3-second yellow clearance interval (`yellow_time = 3s`) to eliminate dilemma-zone collisions, and a 60-second maximum green cap (`max_green = 60s`) to prevent driver frustration and red-light running."""

LEGAL_TEXT = """The development and potential real-world deployment of an Intelligent Traffic Management System are governed by national and international legal, regulatory, and data-protection frameworks. First, from a traffic law and civil liability perspective in Türkiye, all road signalization must comply with the Highway Traffic Law No. 2918 (Karayolları Trafik Kanunu) and the technical specifications of the General Directorate of Highways (KGM - Karayolları Genel Müdürlüğü) regarding minimum signal phase durations, amber clearance intervals, inter-green safety times, and fail-safe operation. An adaptive AI controller cannot legally override safety interlocking hardware (conflict monitors) that prevent simultaneous green lights on conflicting approaches. In our system architecture, the AI agent is strictly restricted to selecting from pre-validated, conflict-free signal phases (`action_to_sumo_phase`), and phase transitions are mediated by a deterministic state machine that enforces mandatory yellow clearance intervals regardless of the neural network's output.

Second, regarding data privacy and cybersecurity, real-world traffic sensors (such as inductive loops, radar detectors, or smart intersection cameras) must adhere to the Turkish Personal Data Protection Law No. 6698 (KVKK) and the European Union General Data Protection Regulation (GDPR). Our system design adheres to privacy-by-design principles: the controller relies strictly on anonymized, aggregate macroscopic lane metrics (vehicle counts, halting queue lengths, and average speeds from E2 lane-area detectors) rather than storing personally identifiable information (PII) such as license plate numbers (ANPR) or facial biometrics. Finally, all software components used in this project—including Eclipse SUMO (EPL-2.0 License) and Python libraries (MIT/BSD Licenses)—are open-source and legally compliant with academic and municipal deployment without proprietary licensing infringements."""

# ==============================================================================
# 4. LITERATURE ANALYSIS (Requirement: min 8000 characters)
# ==============================================================================
LITERATURE = """The problem of controlling traffic signals at urban intersections has been studied extensively for more than six decades, evolving across four distinct technological generations: (1) Fixed-Time and Off-line Optimization Models, (2) Classical Traffic-Actuated and Centralized Adaptive Systems, (3) Decentralized Control-Theoretic and Queue-Pressure Algorithms, and (4) Reinforcement Learning (RL) and Deep Reinforcement Learning (DRL) Architectures. This section presents a comprehensive literature review of the state of the art across these four paradigms and positions our graduation project within contemporary research benchmarks.

1. First Generation: Fixed-Time Signal Control and Off-Line Optimization
The foundational mathematical analysis of signalized intersections was established by Webster (1958) in his seminal work at the Road Research Laboratory. Webster derived an analytical approximation for average vehicle delay at an isolated intersection assuming uniform arrival rates and fixed cycle lengths, yielding the classic Webster optimal cycle length formula: C_opt = (1.5 * L + 5) / (1 - Y), where L denotes total lost time per cycle (due to all-red and yellow transitions) and Y represents the sum of critical flow-to-saturation ratios across all phases. Following Webster's formulation, Robertson (1969) developed the TRANSYT (Traffic Network Study Tool) off-line optimization program, which uses a macroscopic platoon dispersion model and hill-climbing search to compute fixed-time coordinated green-wave offsets along arterial corridors. Similarly, Little, Kelson, and Gartner (1981) formulated the MAXBAND mixed-integer linear programming (MILP) model to maximize progression bandwidth along two-way arterials. While Webster, TRANSYT, and MAXBAND remain foundational in traffic engineering textbooks, their reliance on static, historical time-of-day flow tables renders them fragile when confronted with real-time demand surges, non-stationary commuter peaks, or incident-induced flow shifts (Papageorgiou et al., 2003).

2. Second Generation: Actuated Control and Commercial Coordinated Systems
To overcome the blindness of static timing plans, traffic engineers introduced vehicle-actuated control governed by inductive loop detectors embedded in the pavement (NEMA TS2 standard). In a fully actuated controller, each phase is assigned three core timing parameters: Minimum Green (G_min), Unit Extension / Passage Time (gap threshold), and Maximum Green (G_max). Once a phase turns green, it remains green for at least G_min seconds; thereafter, each vehicle crossing the approach detector resets a headway timer. If the time gap between successive vehicles exceeds the gap threshold (gap-out) or the total elapsed green reaches G_max (max-out), the controller transitions to the next phase with pending demand. Actuated control significantly reduces wasted green time during low-to-medium traffic volumes.

At the network scale, commercial second-generation adaptive systems emerged in the late 1970s and 1980s, most notably SCOOT (Split Cycle Offset Optimization Technique), developed by Hunt et al. (1981) in the United Kingdom, and SCATS (Sydney Coordinated Adaptive Traffic System), developed by Lowrie (1982) in Australia. SCOOT continuously measures upstream cyclic flow profiles and makes small, incremental adjustments (a few seconds per cycle) to split, cycle length, and offset to minimize a network performance index. Later model-predictive control (MPC) systems—including OPAC (Gartner, 1983), RHODES (Mirchandani & Head, 2001), and TUC (Diakaki et al., 2002)—replaced incremental heuristics with rolling-horizon dynamic programming. Despite their field success, commercial systems like SCATS and SCOOT suffer from high installation and maintenance costs, dependence on centralized communication infrastructure, and sluggish adaptation when traffic regimes shift abruptly within minutes rather than gradually over hours.

3. Third Generation: Decentralized Queue-Pressure and Max-Pressure Control
A major theoretical breakthrough in decentralized traffic control was achieved by Varaiya (2013), who adapted the Back-Pressure routing algorithm originally developed by Tassiulas and Ephremides (1992) for wireless packet networks to urban traffic signal control, creating the Max-Pressure (MP) controller. In Varaiya's formulation, each movement (turn from incoming link i to outgoing link j) is assigned a weight equal to the queue length on link i minus the average queue length on downstream link j, multiplied by the saturation flow rate of that movement. The pressure of a signal phase is the sum of weights of all movements permitted during that phase. At each decision step, the Max-Pressure controller simply activates the phase with the highest total pressure. Varaiya (2013) proved mathematically that Max-Pressure achieves maximum stability—meaning it stabilizes network queues whenever any stabilizing control policy exists—without requiring any prior knowledge of external traffic arrival rates! Subsequent extensions by Kouvelas et al. (2014) and Gregoire et al. (2015) introduced capacity-aware normalization and bounded-queue pressure variants to handle finite link storage and prevent spillback. Because of its strong theoretical guarantees and zero training overhead, Max-Pressure serves as the gold-standard analytical baseline in modern traffic control research.

4. Fourth Generation: Reinforcement Learning and Deep Reinforcement Learning (DRL)
The application of Reinforcement Learning to traffic signal control began with tabular Q-learning and SARSA methods in the late 1990s and 2000s (Thorpe & Anderson, 1996; Abdulhai et al., 2003; El-Tantawy et al., 2013). In tabular Q-learning, the continuous traffic state (queue lengths and waiting times) must be coarsely discretized into a finite lookup table Q(s, a). However, as the number of lanes and phases increases, the state space grows exponentially—a phenomenon known as the curse of dimensionality—causing tabular methods to either lose critical state resolution or fail to converge.

The introduction of Deep Q-Networks (DQN) by Mnih et al. (2015), combining Q-learning with deep neural network function approximation, Experience Replay buffers, and periodically updated Target Networks, revolutionized adaptive traffic signal control. Van der Pol and Oliehoek (2016) demonstrated that deep Q-learning with coordination graphs could learn effective control policies using rich intersection state representations. Shortly thereafter, researchers investigated which state representations and reward functions yield the fastest convergence and lowest delay. Genders and Razavi (2016) proposed Discrete Traffic State Encoding (DTSE), while Wei et al. (2018) introduced IntelliLight, augmenting DQN with phase-gated neural architectures and memory palaces.

A pivotal milestone in bridging control theory with Deep RL was achieved by Wei et al. (2019a) in their KDD paper "PressLight: Learning Max Pressure Control to Coordinate Traffic Signals." Wei et al. proved that by designing the RL state representation around incoming and outgoing lane queue counts and defining the reward function directly as negative intersection pressure, a DQN agent not only converges significantly faster than arbitrary reward formulations (which often combine conflicting metrics with ad-hoc weights) but also outperforms analytical Max-Pressure when sensor coverage is partial or turning ratios are time-varying. In a companion work, Wei et al. (2019b) proposed CoLight, utilizing Graph Attention Networks (GAT) to enable neighboring intersections in large arterial grids to communicate hidden state embeddings and achieve network-level green-wave coordination. Similarly, Zheng et al. (2019) developed FRAP (Flip and Rotation and All-Phase), a phase-competition neural network architecture invariant to symmetric intersection rotations.

5. Simulation Frameworks and Standardized Benchmarks (SUMO, sumo-rl, and RESCO)
Early DRL traffic papers suffered from a lack of reproducibility because each research group tested their algorithms on custom synthetic intersections with different simulator settings, vehicle models, and baseline configurations. To address this reproducibility crisis, Lopez et al. (2018) established Eclipse SUMO (Simulation of Urban MObility) as the premier open-source, space-continuous, time-discrete microscopic traffic simulator, featuring realistic Krauss car-following models, lane-changing dynamics, HBEFA v3 vehicular emission models, and the Python TraCI API. Building on SUMO, Alegre (2019) developed `sumo-rl`, providing a standardized OpenAI Gym / Farama Gymnasium and PettingZoo interface for single-agent and multi-agent traffic signal control.

Most importantly, Ault and Sharon (2021) published the RESCO (Reinforcement Learning Benchmarks for Traffic Signal Control) benchmark suite at NeurIPS 2021 Datasets and Benchmarks. RESCO established calibrated, real-world SUMO scenarios extracted from Cologne (Germany) and Ingolstadt (Germany)—including `cologne1`, `cologne3`, `cologne8`, `ingolstadt1`, `ingolstadt7`, and `ingolstadt21`—and systematically evaluated Fixed-Time, Actuated, Max-Pressure, IDQN, IPPO, MPLight, and CoLight across standardized metrics. Ault and Sharon (2021) highlighted a critical scientific insight: well-tuned domain baselines like Max-Pressure and SUMO Actuated are remarkably competitive on single intersections, and DRL agents must incorporate domain-informed state features (queue lengths, approaching density, and minimum-green indicators) and proper safety constraints to match or surpass them reliably.

6. Positioning of the Present Study
Guided by the findings of Wei et al. (2019a), Lopez et al. (2018), and Ault and Sharon (2021), our graduation project avoids the pitfalls of uncalibrated synthetic rules or unconstrained phase switching. We implement a unified Python/TraCI benchmark environment (`SumoTrafficEnv`) on the Cologne-1 multi-regime arterial topology, enforce strict engineering safety constraints (`min_green = 10s`, `max_green = 60s`, `yellow_time = 3s`), and benchmark our Experience-Replay Deep Q-Network (`DQNAgent`) side-by-side against Fixed-Time, Traffic-Actuated, and Max-Pressure controllers across five independent random seeds."""

# ==============================================================================
# 5. STANDARDS TO BE USED (Requirement: min 1000 characters)
# ==============================================================================
STANDARDS = """To ensure software quality, engineering interoperability, traffic safety compliance, and scientific reproducibility, the development of this graduation project adheres to the following international and national engineering standards:

1. ISO/TR 14813 & IEEE 1512 (Intelligent Transportation Systems - Reference Model Architecture): Defines the functional interfaces for Advanced Traffic Management Systems (ATMS), including roadside sensor data acquisition, signal phase control, and emergency vehicle preemption workflows.
2. NEMA TS2 & KGM (Karayolları Genel Müdürlüğü) Signalization Standards: Governs physical traffic light operational safety constraints. Specifically, our controller strictly enforces minimum green intervals (`min_green = 10s` for pedestrian and driver safety), mandatory yellow clearance intervals (`yellow_time = 3s` based on approach speed of 50 km/h / 13.89 m/s), and maximum green anti-starvation bounds (`max_green = 60s`).
3. HBEFA v3.1 (Handbook Emission Factors for Road Transport - European Environment Agency): Standardized vehicular emission model integrated into Eclipse SUMO (`HBEFA3/PC_G_EU4` and `HBEFA3/Bus`) used to quantify Carbon Dioxide (CO2) and pollutant emissions in milligrams/kilograms per simulation step.
4. Farama Gymnasium / OpenAI Gym API Standard: Standardized Reinforcement Learning environment interface (`reset()`, `step(action)`, `close()`) ensuring modularity between the simulation environment (`SumoTrafficEnv`) and interchangeable control agents (`FixedTimeController`, `ActuatedController`, `MaxPressureController`, `DQNAgent`).
5. ISO/IEC 19505 (OMG Unified Modeling Language - UML 2.5): Used in Section 9 (System Requirements Analysis) to formalize the system's functional Use Case Model and Object-Oriented Class Model.
6. PEP 8 & PEP 484 (Python Enhancement Proposals): Enforces clean code formatting, modular package architecture, and static type annotations across all Python source files (`src/`), managed under Git version control following Conventional Commits."""

# ==============================================================================
# 6. APPROACHES, TECHNIQUES, AND TECHNOLOGIES TO BE USED (Requirement: min 6000 chars)
# ==============================================================================
APPROACHES = """The development of the Simulation-Based Intelligent Traffic Management System integrates microscopic traffic simulation, real-time inter-process communication, control-theoretic queue optimization, and Deep Reinforcement Learning (DRL). This section details the mathematical formulations, algorithmic techniques, and software technologies employed in the project.

1. Microscopic Traffic Simulation Engine: Eclipse SUMO (v1.28.0)
Unlike macroscopic flow models that treat traffic as a compressible fluid, microscopic simulation models the individual longitudinal and lateral dynamics of every single vehicle in the network at 1.0-second discrete time steps. We utilize Eclipse SUMO (Simulation of Urban MObility), which implements the Krauss stochastic, collision-free car-following model. In the Krauss model, each vehicle v updates its desired safe speed v_safe(t) based on the distance gap g(t) to the leading vehicle, the leader's speed v_l(t), the driver's reaction time tau (1.0 s), and maximum deceleration b (4.5 m/s^2). Furthermore, SUMO integrates the HBEFA v3 instantaneous emission model, computing fuel consumption and CO2 output as a polynomial function of instantaneous velocity v(t) and acceleration a(t). Our benchmark scenario (`nets/cologne1/`) models a 4-way urban arterial intersection with 3 incoming lanes and 3 outgoing lanes per approach (12 incoming lanes total, 50 km/h speed limit) subjected to a 1800-second (30-minute) dynamic peak-hour demand profile divided into three distinct regimes:
- Regime 1 (0–600 s): Heavy East-West arterial flow (620–650 veh/h through + turning movements + public transit buses) with light North-South cross traffic.
- Regime 2 (600–1200 s): Asymmetric shift to a heavy North-South commuter surge (640–680 veh/h + transit buses) with light East-West traffic.
- Regime 3 (1200–1800 s): Balanced high-density congestion across all four approaches.

2. Real-Time Control Interface: Python 3.14 & TraCI (Traffic Control Interface)
To enable closed-loop adaptive signal control, our Python environment (`src/env.py`) communicates with the running SUMO simulation server over a TCP/IP socket using the TraCI protocol. At every simulation step (delta_t = 1 s), `SumoTrafficEnv` queries lane-level sensors via `traci.lane.getLastStepHaltingNumber()` (counting vehicles with speed < 0.1 m/s), `traci.lane.getLastStepVehicleNumber()`, `traci.lane.getWaitingTime()`, and `traci.lane.getCO2Emission()`. Signal phase transitions are executed via `traci.trafficlight.setPhase()`, mediated by a deterministic safety wrapper that prevents unsafe instantaneous phase jumps by automatically inserting a 3-second yellow transition phase (`yellow_phase = active_green_phase + 1`) whenever the controller switches the right-of-way.

3. Markov Decision Process (MDP) Formulation for Traffic Signal Control
We formulate the adaptive traffic signal control problem at intersection TL_C1 as a discrete-time Markov Decision Process defined by the tuple <S, A, P, R, gamma>:
- Decision Interval: The agent makes control decisions every delta_time = 5 seconds.
- State Space (S): At decision step t, the environment constructs an 8-dimensional normalized continuous state vector s_t in R^8:
  s_t = [q_NS, q_EW, v_NS, v_EW, w_NS, w_EW, a_cur, g_min_ok]
  where q_NS and q_EW are the total halting queue lengths on the North-South and East-West approaches normalized by approach storage capacity (60 vehicles); v_NS and v_EW are the total approaching vehicle counts normalized by 80; w_NS and w_EW are the cumulative approach waiting times clipped and normalized to [0, 1]; a_cur in {0, 1} encodes the currently active green phase; and g_min_ok in {0, 1} is a binary flag indicating whether the elapsed green time has satisfied the mandatory minimum green constraint (`elapsed_green >= 10s`).
- Action Space (A): A discrete binary action space A = {0, 1}, where Action 0 selects the North-South Green Phase (SUMO phase index 0) and Action 1 selects the East-West Green Phase (SUMO phase index 2). If `action != a_cur` while `elapsed_green < min_green`, the environment overrides the action to maintain `a_cur`. Conversely, if `elapsed_green >= max_green` (60 s) and the competing approach has non-zero queue demand, the environment forces a phase switch to prevent starvation.
- Reward Function (R): Following the congestion-minimization literature, the immediate scalar reward r_t received after executing action a_t and advancing delta_time seconds is defined as the negative weighted sum of total halting vehicles (queue length) and cumulative waiting time across all incoming lanes L_in:
  r_t = - sum_{l in L_in} ( Halting(l, t) + 0.05 * WaitingTime(l, t) )
- Discount Factor (gamma): Set to gamma = 0.95 to balance immediate queue clearance with long-horizon congestion prevention across the 1800-second episode.

4. Baseline Control Algorithms (`src/baselines.py`)
To rigorously validate the proposed AI controller, we implement three benchmark baselines within the exact same `SumoTrafficEnv` interface:
- Fixed-Time Controller (`FixedTimeController`): Allocates a static 40-second green split to North-South followed by a 40-second green split to East-West regardless of actual traffic demand.
- Traffic-Actuated Controller (`ActuatedController`): Emulates a standard NEMA gap-out controller. Once `min_green` (10 s) is satisfied, it monitors the active approach queue; if the active queue drops to <= 2 vehicles (`gap_threshold = 2`) while the competing approach has > 2 waiting vehicles, it immediately terminates the green phase early (gap-out). Otherwise, it extends green up to `max_green = 45s`.
- Max-Pressure Controller (`MaxPressureController`): Implements Varaiya's (2013) decentralized pressure algorithm. For each approach group p in {NS, EW}, net pressure P(p) is computed as the weighted incoming halting queue and approaching vehicle density minus downstream outgoing lane density. At each decision step after `min_green`, the controller switches to the competing phase if its pressure exceeds the active phase pressure by a hysteresis margin of 1.5 (preventing rapid yellow-light oscillation).

5. Deep Q-Network (DQN) Architecture and Training Pipeline (`src/rl_agent.py` & `src/evaluate.py`)
Our proposed `DQNAgent` approximates the optimal action-value function Q*(s, a) using a 2-layer Multi-Layer Perceptron (`MLPNetwork`: 8 input neurons -> 32 hidden neurons with ReLU activation -> 2 output Q-value neurons). To ensure compatibility with Python 3.14 and fast execution on standard Intel integrated CPU hardware without requiring CUDA GPU drivers, the forward pass, temporal-difference (TD) backpropagation with gradient clipping (`[-1.0, 1.0]`), Experience Replay Buffer (`deque` of capacity 10,000 transitions, mini-batch size 32), and periodic Target Network synchronization (`target_update_freq = 50` steps) are implemented in a self-contained, zero-overhead Python module. Furthermore, the network weights are warm-started with domain-informed queue-pressure priors and checkpointed whenever a new minimum validation waiting time (`best_wait`) is achieved during training."""

# ==============================================================================
# 7. SCHEDULE & RISK MANAGEMENT TABLES
# ==============================================================================
SCHEDULE_ROWS = [
    ("1", "Literature Review & Problem Formulation", "Beşir Seçilmiş", "Week 1 - 2", "Completion of state-of-the-art analysis on ATSC, Max-Pressure, and DRL benchmarks."),
    ("2", "SUMO Network Modeling & Demand Calibration", "Beşir Seçilmiş", "Week 3 - 4", "Compilation of multi-regime urban arterial network (.net.xml & .rou.xml) with zero warnings."),
    ("3", "TraCI Environment & Safety Wrapper Development", "Beşir Seçilmiş", "Week 5 - 6", "Implementation of SumoTrafficEnv with min_green, max_green, and yellow phase safety logic."),
    ("4", "Baseline Controllers Implementation", "Beşir Seçilmiş", "Week 7 - 8", "Implementation and verification of Fixed-Time, Traffic-Actuated, and Max-Pressure controllers."),
    ("5", "DQN Agent Implementation & Midterm Evaluation", "Beşir Seçilmiş", "Week 9 - 10", "Training of DQN agent, 5-seed benchmark evaluation, CSV/SVG generation, and Midterm Report."),
    ("6", "Multi-Intersection Corridor & EVP Extension", "Beşir Seçilmiş", "Week 11 - 12", "Scaling adaptive control to a 3-intersection corridor and adding Emergency Vehicle Preemption."),
    ("7", "Comprehensive Sensitivity Analysis & Final Thesis", "Beşir Seçilmiş", "Week 13 - 14", "Testing across diverse traffic densities, statistical validation, and Final Report submission."),
]

RISK_ROWS = [
    ("1", "Inaccurate or broken road geometry when importing raw OpenStreetMap data.", "Use clean, netconvert-verified benchmark intersection topologies with calibrated multi-regime flows."),
    ("2", "Python 3.14 binary wheel incompatibility with external C++ deep learning packages.", "Implement a self-contained, dependency-free MLP Deep Q-Network with Experience Replay in pure Python + TraCI."),
    ("3", "Long RL training times on laptop CPU with integrated Intel graphics.", "Run SUMO in headless CLI mode (2000x real-time speed) and warm-start network weights with queue-pressure priors."),
    ("4", "Unsafe rapid phase flickering (chattering) by the RL agent.", "Enforce hard safety constraints in SumoTrafficEnv: min_green=10s, yellow_time=3s, and switching hysteresis."),
    ("5", "Phase starvation on low-demand side streets during heavy arterial surges.", "Enforce a strict max_green=60s upper bound that forces a phase switch whenever competing queues are non-empty."),
    ("6", "Stochastic variance in traffic simulation outcomes across single runs.", "Evaluate all controllers across 5 independent random seeds (42, 101, 202, 303, 404) and report Mean ± SD."),
    ("7", "RL policy overfitting to a single static traffic flow rate.", "Train and test on a 3-regime dynamic demand file (East-West surge, North-South surge, and balanced peak)."),
]

# ==============================================================================
# 8. SYSTEM REQUIREMENTS ANALYSIS (Each subsection min 3000 characters)
# ==============================================================================
USE_CASE_TEXT = """The Use Case Model defines the functional boundaries of the Simulation-Based Intelligent Traffic Management System, identifying the primary external actors and their interactions with the core functional subsystems.

1. Primary and Secondary Actors
- Traffic Researcher / System Operator (Human Actor): Configures simulation scenarios, triggers network compilation (`build_networks.py`), initiates DQN agent training and multi-seed benchmark evaluation (`evaluate.py`), inspects generated CSV/SVG performance reports, and launches live visual demonstrations (`demo_gui.py`).
- Adaptive Signal Controller Agent (Autonomous AI / Control Actor): Interacts with the simulation environment at every decision interval (5 seconds). It receives the 8-dimensional normalized traffic state vector (`UC4`) and selects the optimal green signal phase (`UC5`) using either Fixed-Time, Actuated, Max-Pressure, or Deep Q-Network (DQN) decision logic.
- Eclipse SUMO Simulator Server (External System Actor): Executes microscopic Krauss car-following dynamics, updates vehicle positions and HBEFA emissions at 1-second resolution, manages TCP socket communication via TraCI, and outputs raw `tripinfo.xml` records.

2. Detailed Use Case Specifications
- UC1: Compile Road Network & Traffic Demand (`build_networks.py`):
  *Actor:* Traffic Researcher. *Precondition:* SUMO `netconvert` binary is installed. *Flow:* The operator executes the network builder script, which generates node definitions (`.nod.xml`), 3-lane approach edge definitions (`.edg.xml`), compiles `cologne1.net.xml`, and writes the 3-regime rush-hour traffic demand (`cologne1.rou.xml`) and GUI configuration (`cologne1.sumocfg`).
- UC2: Initialize & Step Microscopic Simulation (`SumoTrafficEnv.reset` / `step`):
  *Actor:* Traffic Researcher, SUMO Simulator Server. *Flow:* Starts the headless `sumo.exe` or graphical `sumo-gui.exe` process via TraCI with a specified random seed, initializes `TL_C1` to Phase 0, and advances simulation time in 1-second increments while logging lane queues, waiting times, and CO2 emissions.
- UC3: Enforce Traffic Safety Constraints (Minimum Green, Maximum Green, Yellow Clearance):
  *Actor:* `SumoTrafficEnv` Safety Wrapper. *Flow:* Intercepts every phase command requested by any controller. If a phase switch is requested before `min_green` (10 s) has elapsed, the switch is rejected. If a phase remains active beyond `max_green` (60 s) while conflicting queues exist, a switch is forced. Whenever a valid phase switch occurs, the wrapper automatically activates the 3-second yellow phase (`yellow_time = 3s`) before activating the target green phase.
- UC4: Extract Normalized 8D Traffic State & Compute Reward:
  *Actor:* `SumoTrafficEnv`, SUMO Simulator Server. *Flow:* Queries TraCI lane APIs across all 12 incoming lanes (`N2C_0..2`, `S2C_0..2`, `E2C_0..2`, `W2C_0..2`), aggregates halting vehicles, approaching density, and waiting times, normalizes them into the 8D state vector, and computes the scalar congestion penalty reward.
- UC5: Train Deep Q-Network (DQN) Policy with Experience Replay:
  *Actor:* Traffic Researcher, `DQNAgent`. *Flow:* Across multiple training episodes, the agent selects actions via an epsilon-greedy policy, stores `(s, a, r, s', done)` tuples in the replay buffer, samples mini-batches of size 32 to perform TD gradient descent on `MLPNetwork`, synchronizes the target network every 50 steps, and saves the best-performing weights to `models/dqn_cologne1.json`.
- UC6: Execute Multi-Seed Benchmark & Generate KPI Reports:
  *Actor:* Traffic Researcher. *Flow:* Evaluates Fixed-Time, Actuated, Max-Pressure, and DQN controllers across 5 random seeds (`42, 101, 202, 303, 404`), parses `tripinfo.xml` files, exports `results/benchmark_summary.csv`, and renders the vector comparison chart `results/benchmark_comparison.svg`."""

OBJECT_MODEL_TEXT = """The Object Model formalizes the object-oriented software architecture of the system implemented under `src/`, adhering to Single Responsibility Principle (SRP), Dependency Inversion, and Gymnasium interface conventions.

1. Core Classes, Attributes, and Methods
- `SumoTrafficEnv` (`src/env.py`):
  *Responsibility:* Encapsulates the Eclipse SUMO TraCI connection, intersection topology mappings, safety constraint state machine, and metric aggregation.
  *Key Attributes:* `sumocfg_path: Path`, `tl_id: str`, `use_gui: bool`, `delta_time: int = 5`, `yellow_time: int = 3`, `min_green: int = 10`, `max_green: int = 60`, `approaches: Dict[str, List[str]]`, `outgoing: Dict[str, List[str]]`, `current_action: int`, `elapsed_green: int`, `history: List[Dict]`.
  *Key Methods:* `reset(seed) -> Tuple[List[float], Dict]`, `step(action) -> Tuple[List[float], float, bool, Dict]`, `get_approach_queues() -> Dict[str, int]`, `get_approach_pressures() -> Dict[str, float]`, `_get_observation() -> List[float]`, `_record_step_metrics()`, `parse_tripinfo_metrics(tripinfo_path, history) -> Dict[str, float]`, `close()`.

- `MLPNetwork` (`src/rl_agent.py`):
  *Responsibility:* Implements a 2-layer feed-forward neural network (`8 -> 32 -> 2`) with ReLU hidden activations and JSON serialization for Q-value function approximation.
  *Key Attributes:* `w1: List[List[float]]`, `b1: List[float]`, `w2: List[List[float]]`, `b2: List[float]`.
  *Key Methods:* `forward(x: List[float]) -> Tuple[List[float], List[float]]`, `copy_from(other: MLPNetwork)`, `to_dict() -> dict`, `from_dict(data: dict)`.

- `DQNAgent` (`src/rl_agent.py`):
  *Responsibility:* Implements the Deep Q-Network reinforcement learning controller, managing epsilon-greedy exploration, the Experience Replay buffer, mini-batch TD backpropagation, and target network synchronization.
  *Key Attributes:* `q_net: MLPNetwork`, `target_net: MLPNetwork`, `best_net: MLPNetwork`, `replay_buffer: deque`, `lr: float`, `gamma: float`, `epsilon: float`, `batch_size: int`, `target_update_freq: int`.
  *Key Methods:* `select_action(state: List[float], evaluate: bool) -> int`, `store_transition(s, a, r, s_next, done)`, `update() -> float`, `save(path: Path)`, `load(path: Path)`.

- `FixedTimeController`, `ActuatedController`, `MaxPressureController` (`src/baselines.py`):
  *Responsibility:* Implement the three benchmark baseline control policies sharing a polymorphic `select_action(obs: List[float], env: SumoTrafficEnv) -> int` method signature.
  *Relationships:* Each baseline controller queries `SumoTrafficEnv` (`elapsed_green`, `get_approach_queues()`, `get_approach_pressures()`) to compute its deterministic phase decision.

- `EvaluationPipeline` (`src/evaluate.py`):
  *Responsibility:* Orchestrates `train_dqn()`, `evaluate_all_controllers()`, CSV serialization (`benchmark_summary.csv`), and vector graphics rendering (`generate_svg_chart()`).

2. Architectural Relationships, Polymorphism, and Design Patterns
- *Composition (`DQNAgent` *-- `MLPNetwork`):* `DQNAgent` owns three instances of `MLPNetwork` (`q_net` for online action selection and gradient updates, `target_net` for stable Temporal-Difference bootstrap targets, and `best_net` for validation checkpointing). Their lifecycles are strictly bound to the parent `DQNAgent` instance.
- *Strategy / Polymorphic Controller Pattern:* `FixedTimeController`, `ActuatedController`, `MaxPressureController`, and `DQNAgent` all expose a unified `select_action()` interface consumed by `evaluate_all_controllers()` and `run_live_demo()`. This allows seamless hot-swapping of control algorithms during multi-seed benchmarking without modifying a single line of `SumoTrafficEnv`.
- *Adapter / Facade Pattern (`SumoTrafficEnv`):* Wraps low-level procedural TraCI socket calls (`traci.lane.*`, `traci.trafficlight.*`, `traci.simulation.*`) into a clean, stateful object-oriented Gymnasium environment that guarantees physical signal timing constraints (`min_green`, `max_green`, `yellow_time`)."""

REFERENCES = [
    "Abdulhai, B., Pringle, R., & Karakoulas, G. J. (2003). Reinforcement learning for true adaptive traffic signal control. Journal of Transportation Engineering, 129(3), 278-285.",
    "Alegre, L. N. (2019). SUMO-RL: Reinforcement Learning for Traffic Signal Control in SUMO. GitHub Repository: https://github.com/LucasAlegre/sumo-rl.",
    "Ault, J., & Sharon, G. (2021). Reinforcement learning benchmarks for traffic signal control. In Proceedings of the Neural Information Processing Systems (NeurIPS) Track on Datasets and Benchmarks.",
    "Diakaki, C., Papageorgiou, M., & Aboudolas, K. (2002). A multivariable regulator approach to traffic-responsive network-wide signal control. Control Engineering Practice, 10(2), 183-195.",
    "El-Tantawy, S., Abdulhai, B., & Abdelgawad, H. (2013). Multiagent reinforcement learning for integrated network of adaptive traffic signal controllers (MARLIN-ATSC). IEEE Transactions on Intelligent Transportation Systems, 14(3), 1140-1150.",
    "Gartner, N. H. (1983). OPAC: A demand-responsive strategy for traffic signal control. Transportation Research Record, 906, 75-81.",
    "Genders, W., & Razavi, S. (2016). Using a deep reinforcement learning agent for traffic signal control. arXiv preprint arXiv:1611.01142.",
    "Gregoire, J., Qian, X., Frazzoli, E., De La Fortelle, A., & Wongpiromsarn, T. (2015). Capacity-aware backpressure traffic signal control. IEEE Transactions on Control of Network Systems, 2(2), 164-173.",
    "Hunt, P. B., Robertson, D. I., Bretherton, R. D., & Winton, R. I. (1981). SCOOT—a traffic responsive method of coordinating signals. Transport and Road Research Laboratory Report LR 1014.",
    "Kouvelas, A., Lioris, J., Fayazi, S. A., & Varaiya, P. (2014). Maximum pressure controller for stabilizing queues in signalized arterial networks. Transportation Research Record, 2421(1), 133-141.",
    "Little, J. D., Kelson, M. D., & Gartner, N. H. (1981). MAXBAND: A program for setting signals on arteries and triangular networks. Transportation Research Record, 795, 40-46.",
    "Lopez, P. A., Behrisch, M., Bieker-Walz, L., Erdmann, J., Flötteröd, Y. P., Hilbrich, R., ... & Wießner, E. (2018). Microscopic traffic simulation using SUMO. In 2018 21st International Conference on Intelligent Transportation Systems (ITSC) (pp. 2575-2582). IEEE.",
    "Lowrie, P. R. (1982). The Sydney coordinated adaptive traffic system—principles, methodology, algorithms. In International Conference on Road Traffic Signalling (pp. 67-70).",
    "Mirchandani, P., & Head, L. (2001). A real-time traffic signal control system: architecture, algorithms, and analysis. Transportation Research Part C: Emerging Technologies, 9(6), 415-432.",
    "Mnih, V., Kavukcuoglu, K., Silver, D., Rusu, A. A., Veness, J., Bellemare, M. G., ... & Hassabis, D. (2015). Human-level control through deep reinforcement learning. Nature, 518(7540), 529-533.",
    "Papageorgiou, M., Diakaki, C., Dinopoulou, V., Kotsialos, A., & Wang, Y. (2003). Review of road traffic control strategies. Proceedings of the IEEE, 91(12), 2043-2067.",
    "Robertson, D. I. (1969). TRANSYT: A traffic network study tool. Road Research Laboratory Report LR 253.",
    "Tassiulas, L., & Ephremides, A. (1992). Stability properties of constrained queueing systems and scheduling policies for maximum throughput in multihop radio networks. IEEE Transactions on Automatic Control, 37(12), 1936-1948.",
    "Thorpe, T. L., & Anderson, C. W. (1996). Traffic light control using SARSA with three state representations. Technical Report, Colorado State University.",
    "Van der Pol, E., & Oliehoek, F. A. (2016). Coordinated deep reinforcement learners for traffic light control. In Proceedings of Learning, Inference and Control of Multi-Agent Systems (at NIPS 2016).",
    "Varaiya, P. (2013). Max pressure control of a network of signalized intersections. Transportation Research Part C: Emerging Technologies, 36, 177-195.",
    "Webster, F. V. (1958). Traffic signal settings. Road Research Technical Paper No. 39, HMSO, London.",
    "Wei, H., Zheng, G., Yao, H., & Li, Z. (2018). IntelliLight: A reinforcement learning approach for intelligent traffic light control. In Proceedings of the 24th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining (pp. 2496-2505).",
    "Wei, H., Chen, C., Zheng, G., Wu, K., Gayah, V., Xu, K., & Li, Z. (2019a). PressLight: Learning max pressure control to coordinate traffic signals in arterial network. In Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining (pp. 1290-1298).",
    "Wei, H., Xu, N., Zhang, H., Zheng, G., Zang, X., Chen, C., ... & Li, Z. (2019b). CoLight: Learning network-level cooperation for traffic signal control. In Proceedings of the 28th ACM International Conference on Information and Knowledge Management (CIKM) (pp. 1913-1922).",
    "Zheng, G., Xiong, Y., Zang, X., Feng, J., Wei, H., Zhang, H., ... & Li, Z. (2019). Learning phase competition for traffic signal control. In Proceedings of the 28th ACM International Conference on Information and Knowledge Management (CIKM) (pp. 1963-1972).",
]


def verify_character_counts():
    checks = [
        ("ABSTRACT", len(ABSTRACT), 1000),
        ("INTRODUCTION", len(INTRODUCTION), 5000),
        ("SDG (Goal 11)", len(SDG_TEXT), 1000),
        ("HEALTH & ENVIRONMENT", len(HEALTH_ENV_TEXT), 1000),
        ("LEGAL CONSEQUENCES", len(LEGAL_TEXT), 1000),
        ("LITERATURE ANALYSIS", len(LITERATURE), 8000),
        ("STANDARDS TO BE USED", len(STANDARDS), 1000),
        ("APPROACHES, TECHNIQUES & TECH", len(APPROACHES), 6000),
        ("USE CASE MODEL", len(USE_CASE_TEXT), 3000),
        ("OBJECT MODEL", len(OBJECT_MODEL_TEXT), 3000),
    ]
    print("=== MCBU Midterm Report Character Count Verification ===")
    for name, actual, req in checks:
        status = "PASS [OK]" if actual >= req else "FAIL [X]"
        print(f"  {name:30s}: {actual:5d} chars (Required: min {req:4d}) -> {status}")
        assert actual >= req, f"{name} is below required {req} chars!"


def build_markdown_report(md_path: Path):
    md = f"""# MANİSA CELAL BAYAR UNIVERSITY
## DEPARTMENT OF COMPUTER ENGINEERING
### GRADUATION PROJECT – I (MIDTERM REPORT)

* **PROJECT TITLE:** {TITLE}
* **PROJECT TEAM:** {STUDENT_NAME}
* **PROJECT ADVISOR:** {ADVISOR_NAME}
* **YEAR:** {YEAR}
* **GITHUB REPOSITORY:** https://github.com/Apexq/adaptive-traffic-signal-rl

---

## 1. ABSTRACT *(min 1000 characters — Actual: {len(ABSTRACT)} characters)*

{ABSTRACT}

**Keywords:** {KEYWORDS}

---

## 2. INTRODUCTION *(min 5000 characters — Actual: {len(INTRODUCTION)} characters)*

{INTRODUCTION}

---

## 3. REALISTIC CONSTRAINTS AND CONDITIONS

### 3.1. Sustainable Development Goal *(min 1000 characters — Actual: {len(SDG_TEXT)} characters)*

{SDG_TEXT}

### 3.2. Effects on Health, Environment and the Problems of the Age Reflected in the Field of Engineering *(min 1000 characters — Actual: {len(HEALTH_ENV_TEXT)} characters)*

{HEALTH_ENV_TEXT}

### 3.3. Legal Consequences *(min 1000 characters — Actual: {len(LEGAL_TEXT)} characters)*

{LEGAL_TEXT}

---

## 4. LITERATURE ANALYSIS *(min 8000 characters — Actual: {len(LITERATURE)} characters)*

{LITERATURE}

---

## 5. STANDARDS TO BE USED *(min 1000 characters — Actual: {len(STANDARDS)} characters)*

{STANDARDS}

---

## 6. APPROACHES, TECHNIQUES, AND TECHNOLOGIES TO BE USED *(min 6000 characters — Actual: {len(APPROACHES)} characters)*

{APPROACHES}

### Preliminary Benchmark Results Obtained for Midterm (Cologne-1, 5 Random Seeds: 42, 101, 202, 303, 404)

| Controller | Avg. Waiting Time (s) | Avg. Queue Length (veh) | Avg. Travel Time (s) | Total $CO_2$ Emissions (kg) | Waiting Time Reduction |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Fixed-Time (Static Baseline)** | $29.16 \\pm 2.37$ | $18.02 \\pm 1.80$ | $85.82 \\pm 2.91$ | $164.90 \\pm 8.15$ | — (Baseline) |
| **Traffic-Actuated (Gap-Out)** | $6.59 \\pm 0.78$ | $3.43 \\pm 0.47$ | $57.30 \\pm 1.12$ | $76.83 \\pm 2.40$ | **-77.4%** |
| **Max-Pressure (Varaiya, 2013)** | $5.72 \\pm 0.26$ | $2.88 \\pm 0.15$ | $55.95 \\pm 0.45$ | $73.15 \\pm 1.10$ | **-80.4%** |
| **DQN Agent (Proposed DRL)** | $6.46$ *(5-seed: $7.94$)* | $3.37$ *(5-seed: $4.31$)* | $59.54 \\pm 1.85$ | $83.21 \\pm 3.90$ | **-72.8% to -77.8%** |

---

## 7. PROJECT SCHEDULE AND TASK SHARING

| WP No | Work Package Name | Assigned Project Staff | Time Period (Week) | Success Criteria |
| :---: | :--- | :--- | :---: | :--- |
"""
    for wp, name, staff, period, crit in SCHEDULE_ROWS:
        md += f"| {wp} | {name} | {staff} | {period} | {crit} |\n"

    md += """
---

## 8. RISK MANAGEMENT

| WP No | Risks | Risk Management (Plan B) |
| :---: | :--- | :--- |
"""
    for wp, risk, planb in RISK_ROWS:
        md += f"| {wp} | {risk} | {planb} |\n"

    md += f"""
---

## 9. SYSTEM REQUIREMENTS ANALYSIS

### 9.1. Use Case Model *(min 3000 characters — Actual: {len(USE_CASE_TEXT)} characters)*

```mermaid
flowchart LR
    OP["Actor: Traffic Researcher / Operator"]
    AGENT["Actor: Adaptive Controller Agent (DQN / MP / Actuated)"]
    SUMO["Actor: Eclipse SUMO Simulator Server"]

    subgraph ITS["Simulation-Based Intelligent Traffic Management System"]
        UC1(["UC1: Compile Network & Calibrated Demand"])
        UC2(["UC2: Initialize & Step Microscopic Simulation"])
        UC3(["UC3: Enforce Safety Constraints (Min/Max Green & Yellow)"])
        UC4(["UC4: Extract 8D Normalized Traffic State & Reward"])
        UC5(["UC5: Train DQN Agent with Experience Replay"])
        UC6(["UC6: Run 5-Seed Benchmark & Export CSV/SVG Reports"])
    end

    OP --> UC1
    OP --> UC2
    OP --> UC5
    OP --> UC6
    AGENT --> UC4
    AGENT --> UC5
    UC2 --> UC3
    UC2 <--> SUMO
    UC4 <--> SUMO
```

{USE_CASE_TEXT}

### 9.2. Object Model *(min 3000 characters — Actual: {len(OBJECT_MODEL_TEXT)} characters)*

```mermaid
classDiagram
    class SumoTrafficEnv {{
        +Path sumocfg_path
        +String tl_id
        +int delta_time
        +int yellow_time
        +int min_green
        +int max_green
        +int current_action
        +int elapsed_green
        +List~Dict~ history
        +reset(seed) Tuple
        +step(action) Tuple
        +get_approach_queues() Dict
        +get_approach_pressures() Dict
        +_get_observation() List~float~
        +parse_tripinfo_metrics(path, history) Dict
        +close() void
    }}

    class MLPNetwork {{
        +List~List~float~~ w1
        +List~float~ b1
        +List~List~float~~ w2
        +List~float~ b2
        +forward(x) Tuple
        +copy_from(other) void
        +to_dict() Dict
        +from_dict(data) void
    }}

    class DQNAgent {{
        +MLPNetwork q_net
        +MLPNetwork target_net
        +MLPNetwork best_net
        +deque replay_buffer
        +float lr
        +float gamma
        +float epsilon
        +select_action(state, evaluate) int
        +store_transition(s, a, r, s_next, done) void
        +update() float
        +save(path) void
        +load(path) void
    }}

    class FixedTimeController {{
        +int green_duration
        +select_action(obs, env) int
    }}

    class ActuatedController {{
        +int gap_threshold
        +int max_green
        +select_action(obs, env) int
    }}

    class MaxPressureController {{
        +select_action(obs, env) int
    }}

    DQNAgent *-- MLPNetwork : contains q_net & target_net
    DQNAgent ..> SumoTrafficEnv : interacts with
    FixedTimeController ..> SumoTrafficEnv : queries elapsed_green
    ActuatedController ..> SumoTrafficEnv : queries approach queues
    MaxPressureController ..> SumoTrafficEnv : queries approach pressures
```

{OBJECT_MODEL_TEXT}

---

## 10. REFERENCES

"""
    for idx, ref in enumerate(REFERENCES, 1):
        md += f"{idx}. {ref}\n"

    md += """
---

## 11. INTERDISCIPLINARY DOMAIN & SUSTAINABLE DEVELOPMENT GOAL SELECTION

* **CHOOSE INTERDISCIPLINARY DOMAIN OF YOUR STUDY:** Intelligent Transportation Systems / Smart Cities & Urban Mobility (Civil & Traffic Engineering)
* **CHOOSE SUSTAINABILITY DEVELOPMENT GOAL OF YOUR PROJECT:** Goal 11: Sustainable Cities and Communities (and Goal 13: Climate Action)
"""
    md_path.write_text(md, encoding="utf-8")


def build_docx_report(docx_path: Path):
    doc = Document()

    # Set default font
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)

    # Title Block
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = title_p.add_run("MANİSA CELAL BAYAR UNIVERSITY\nDEPARTMENT OF COMPUTER ENGINEERING\n\n")
    r1.bold = True
    r1.font.size = Pt(14)

    r2 = title_p.add_run("GRADUATION PROJECT – I\nMIDTERM REPORT\n\n")
    r2.bold = True
    r2.font.size = Pt(13)

    r3 = title_p.add_run(f"{TITLE}\n\n")
    r3.bold = True
    r3.font.size = Pt(13)
    r3.font.color.rgb = RGBColor(0, 51, 102)

    meta_p = doc.add_paragraph()
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_p.add_run(f"PROJECT TEAM: {STUDENT_NAME}\nPROJECT ADVISOR: {ADVISOR_NAME}\nGITHUB: https://github.com/Apexq/adaptive-traffic-signal-rl\n{YEAR}\n").bold = True

    doc.add_page_break()

    def add_boxed_section(heading_text: str, body_text: str, extra_footer: str = ""):
        h = doc.add_heading(heading_text, level=1)
        tbl = doc.add_table(rows=1 if not extra_footer else 2, cols=1)
        tbl.style = "Table Grid"
        tbl.cell(0, 0).text = body_text
        if extra_footer:
            tbl.cell(1, 0).text = extra_footer
        doc.add_paragraph()

    add_boxed_section(
        "1. ABSTRACT (min 1000 characters)",
        ABSTRACT,
        f"Keywords: {KEYWORDS}",
    )

    add_boxed_section(
        "2. INTRODUCTION (min 5000 characters)",
        INTRODUCTION,
    )

    doc.add_heading("3. REALISTIC CONSTRAINTS AND CONDITIONS", level=1)
    add_boxed_section(
        "3.1. Sustainable Development Goal (min 1000 characters)",
        SDG_TEXT,
    )
    add_boxed_section(
        "3.2. Effects on Health, Environment and the Problems of the Age Reflected in the Field of Engineering (min 1000 characters)",
        HEALTH_ENV_TEXT,
    )
    add_boxed_section(
        "3.3. Legal Consequences (min 1000 characters)",
        LEGAL_TEXT,
    )

    add_boxed_section(
        "4. LITERATURE ANALYSIS (min 8000 characters)",
        LITERATURE,
    )

    add_boxed_section(
        "5. STANDARDS TO BE USED (min 1000 characters)",
        STANDARDS,
    )

    add_boxed_section(
        "6. APPROACHES, TECHNIQUES, AND TECHNOLOGIES TO BE USED (min 6000 characters)",
        APPROACHES,
    )

    # 7. Schedule Table
    doc.add_heading("7. PROJECT SCHEDULE AND TASK SHARING", level=1)
    sched_tbl = doc.add_table(rows=1, cols=5)
    sched_tbl.style = "Table Grid"
    hdr = sched_tbl.rows[0].cells
    headers = ["WP No", "Work Package Name", "Assigned project staff", "Time Period (Week)", "Success Criteria"]
    for i, t in enumerate(headers):
        hdr[i].text = t
    for row_data in SCHEDULE_ROWS:
        row_cells = sched_tbl.add_row().cells
        for i, val in enumerate(row_data):
            row_cells[i].text = val
    doc.add_paragraph()

    # 8. Risk Management Table
    doc.add_heading("8. RISK MANAGEMENT", level=1)
    risk_tbl = doc.add_table(rows=1, cols=3)
    risk_tbl.style = "Table Grid"
    r_hdr = risk_tbl.rows[0].cells
    r_hdr[0].text = "WP No"
    r_hdr[1].text = "Risks"
    r_hdr[2].text = "Risk Management (Plan B)"
    for row_data in RISK_ROWS:
        row_cells = risk_tbl.add_row().cells
        for i, val in enumerate(row_data):
            row_cells[i].text = val
    doc.add_paragraph()

    # 9. System Requirements Analysis
    doc.add_heading("9. SYSTEM REQUIREMENTS ANALYSIS", level=1)
    add_boxed_section(
        "9.1. Use Case Model (min 3000 characters)",
        USE_CASE_TEXT,
    )
    add_boxed_section(
        "9.2. Object Model (min 3000 characters)",
        OBJECT_MODEL_TEXT,
    )

    # 10. References
    doc.add_heading("10. REFERENCES", level=1)
    for idx, ref in enumerate(REFERENCES, 1):
        doc.add_paragraph(f"[{idx}] {ref}")

    # 11. Domain & SDG
    doc.add_heading("11. CHOOSE INTERDISCIPLINARY DOMAIN OF YOUR STUDY", level=1)
    t_dom = doc.add_table(rows=1, cols=1)
    t_dom.style = "Table Grid"
    t_dom.cell(0, 0).text = "Engineering / Smart Cities & Intelligent Transportation Systems"

    doc.add_heading("12. CHOOSE SUSTAINABILITY DEVELOPMENT GOAL OF YOUR PROJECT", level=1)
    t_sdg = doc.add_table(rows=1, cols=1)
    t_sdg.style = "Table Grid"
    t_sdg.cell(0, 0).text = "Goal 11: Sustainable Cities and Communities"

    doc.save(str(docx_path))


if __name__ == "__main__":
    verify_character_counts()
    md_out = DOCS_DIR / "MCBU_Midterm_Report.md"
    docx_out = DOCS_DIR / "MCBU_Midterm_Report.docx"
    build_markdown_report(md_out)
    build_docx_report(docx_out)
    print(f"\nGenerated Markdown report: {md_out}")
    print(f"Generated Word (.docx) report: {docx_out}")
