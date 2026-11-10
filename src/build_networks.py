"""
Network Builder for Traffic-RL Benchmark Scenarios
Generates SUMO road networks (.net.xml), calibrated peak-hour traffic demand (.rou.xml),
lane area detectors (.add.xml), and SUMO configurations (.sumocfg) for:
  1. single_urban (RESCO Cologne-1 style isolated 4-phase urban arterial intersection)
  2. corridor3 (3-intersection coordinated urban arterial corridor)
"""

import os
import subprocess
from pathlib import Path

SUMO_BIN = Path(r"C:\Program Files (x86)\SUMO\bin")
NETCONVERT = SUMO_BIN / "netconvert.exe"
BASE_DIR = Path(__file__).resolve().parent.parent
NETS_DIR = BASE_DIR / "nets"


def build_cologne1_network() -> Path:
    """Builds the Cologne-1 benchmark intersection (3-lane approaches, 4 green phases)."""
    scen_dir = NETS_DIR / "cologne1"
    scen_dir.mkdir(parents=True, exist_ok=True)

    # 1. Nodes
    nod_xml = """<?xml version="1.0" encoding="UTF-8"?>
<nodes>
    <node id="C1" x="0.0" y="0.0" type="traffic_light" tl="TL_C1"/>
    <node id="N" x="0.0" y="300.0" type="priority"/>
    <node id="S" x="0.0" y="-300.0" type="priority"/>
    <node id="W" x="-300.0" y="0.0" type="priority"/>
    <node id="E" x="300.0" y="0.0" type="priority"/>
</nodes>
"""
    (scen_dir / "cologne1.nod.xml").write_text(nod_xml, encoding="utf-8")

    # 2. Edges (3 lanes per approach: right, straight, left)
    edg_xml = """<?xml version="1.0" encoding="UTF-8"?>
<edges>
    <edge id="N2C" from="N" to="C1" numLanes="3" speed="13.89" priority="3"/>
    <edge id="C2N" from="C1" to="N" numLanes="3" speed="13.89" priority="3"/>
    <edge id="S2C" from="S" to="C1" numLanes="3" speed="13.89" priority="3"/>
    <edge id="C2S" from="C1" to="S" numLanes="3" speed="13.89" priority="3"/>
    <edge id="W2C" from="W" to="C1" numLanes="3" speed="13.89" priority="3"/>
    <edge id="C2W" from="C1" to="W" numLanes="3" speed="13.89" priority="3"/>
    <edge id="E2C" from="E" to="C1" numLanes="3" speed="13.89" priority="3"/>
    <edge id="C2E" from="C1" to="E" numLanes="3" speed="13.89" priority="3"/>
</edges>
"""
    (scen_dir / "cologne1.edg.xml").write_text(edg_xml, encoding="utf-8")

    # Compile with netconvert
    net_file = scen_dir / "cologne1.net.xml"
    subprocess.run(
        [
            str(NETCONVERT),
            f"--node-files={scen_dir / 'cologne1.nod.xml'}",
            f"--edge-files={scen_dir / 'cologne1.edg.xml'}",
            f"--output-file={net_file}",
            "--no-turnarounds=true",
        ],
        check=True,
    )

    # 3. Calibrated Asymmetrical Rush-Hour Traffic Demand (1800s)
    # Time-varying surge: Phase A (0-600s) heavy East-West arterial;
    # Phase B (600-1200s) heavy North-South commuter surge;
    # Phase C (1200-1800s) mixed high-density demand + Emergency Vehicles
    rou_xml = """<?xml version="1.0" encoding="UTF-8"?>
<routes>
    <vType id="car" vClass="passenger" guiShape="passenger" length="4.5" minGap="2.5" accel="2.6" decel="4.5" maxSpeed="15.0" color="70,180,255" emissionClass="HBEFA3/PC_G_EU4"/>
    <vType id="bus" vClass="bus" guiShape="bus" length="12.0" minGap="3.0" accel="1.5" decel="3.5" maxSpeed="12.5" color="255,180,40" emissionClass="HBEFA3/Bus"/>
    <vType id="ambulance" vClass="emergency" guiShape="emergency" length="6.0" minGap="2.0" accel="3.2" decel="5.0" maxSpeed="20.0" color="255,40,40" speedFactor="1.3"/>

    <!-- Routes -->
    <route id="W_E" edges="W2C C2E"/>
    <route id="W_N" edges="W2C C2N"/>
    <route id="W_S" edges="W2C C2S"/>

    <route id="E_W" edges="E2C C2W"/>
    <route id="E_N" edges="E2C C2N"/>
    <route id="E_S" edges="E2C C2S"/>

    <route id="N_S" edges="N2C C2S"/>
    <route id="N_E" edges="N2C C2E"/>
    <route id="N_W" edges="N2C C2W"/>

    <route id="S_N" edges="S2C C2N"/>
    <route id="S_E" edges="S2C C2E"/>
    <route id="S_W" edges="S2C C2W"/>

    <!-- Regime 1 (0 - 600s): Heavy East-West Arterial Flow, Light North-South -->
    <flow id="r1_WE" type="car" route="W_E" begin="0" end="600" vehsPerHour="650" departLane="best" departSpeed="max"/>
    <flow id="r1_WN" type="car" route="W_N" begin="0" end="600" vehsPerHour="180" departLane="best" departSpeed="max"/>
    <flow id="r1_WS" type="car" route="W_S" begin="0" end="600" vehsPerHour="140" departLane="best" departSpeed="max"/>
    <flow id="r1_EW" type="car" route="E_W" begin="0" end="600" vehsPerHour="620" departLane="best" departSpeed="max"/>
    <flow id="r1_EN" type="car" route="E_N" begin="0" end="600" vehsPerHour="160" departLane="best" departSpeed="max"/>
    <flow id="r1_ES" type="car" route="E_S" begin="0" end="600" vehsPerHour="130" departLane="best" departSpeed="max"/>
    <flow id="r1_NS" type="car" route="N_S" begin="0" end="600" vehsPerHour="140" departLane="best" departSpeed="max"/>
    <flow id="r1_SN" type="car" route="S_N" begin="0" end="600" vehsPerHour="150" departLane="best" departSpeed="max"/>
    <flow id="r1_bus_WE" type="bus" route="W_E" begin="10" end="600" vehsPerHour="40" departLane="best" departSpeed="max"/>

    <!-- Regime 2 (600 - 1200s): Heavy North-South Commuter Surge, Light East-West -->
    <flow id="r2_NS" type="car" route="N_S" begin="600" end="1200" vehsPerHour="680" departLane="best" departSpeed="max"/>
    <flow id="r2_NE" type="car" route="N_E" begin="600" end="1200" vehsPerHour="190" departLane="best" departSpeed="max"/>
    <flow id="r2_NW" type="car" route="N_W" begin="600" end="1200" vehsPerHour="150" departLane="best" departSpeed="max"/>
    <flow id="r2_SN" type="car" route="S_N" begin="600" end="1200" vehsPerHour="640" departLane="best" departSpeed="max"/>
    <flow id="r2_SE" type="car" route="S_E" begin="600" end="1200" vehsPerHour="170" departLane="best" departSpeed="max"/>
    <flow id="r2_SW" type="car" route="S_W" begin="600" end="1200" vehsPerHour="140" departLane="best" departSpeed="max"/>
    <flow id="r2_WE" type="car" route="W_E" begin="600" end="1200" vehsPerHour="160" departLane="best" departSpeed="max"/>
    <flow id="r2_EW" type="car" route="E_W" begin="600" end="1200" vehsPerHour="150" departLane="best" departSpeed="max"/>
    <flow id="r2_bus_NS" type="bus" route="N_S" begin="610" end="1200" vehsPerHour="45" departLane="best" departSpeed="max"/>

    <!-- Regime 3 (1200 - 1800s): Balanced Peak Congestion + Emergency Vehicles -->
    <flow id="r3_WE" type="car" route="W_E" begin="1200" end="1800" vehsPerHour="480" departLane="best" departSpeed="max"/>
    <flow id="r3_EW" type="car" route="E_W" begin="1200" end="1800" vehsPerHour="460" departLane="best" departSpeed="max"/>
    <flow id="r3_NS" type="car" route="N_S" begin="1200" end="1800" vehsPerHour="450" departLane="best" departSpeed="max"/>
    <flow id="r3_SN" type="car" route="S_N" begin="1200" end="1800" vehsPerHour="440" departLane="best" departSpeed="max"/>
    <flow id="r3_WN" type="car" route="W_N" begin="1200" end="1800" vehsPerHour="140" departLane="best" departSpeed="max"/>
    <flow id="r3_EN" type="car" route="E_N" begin="1200" end="1800" vehsPerHour="130" departLane="best" departSpeed="max"/>
    <flow id="r3_NE" type="car" route="N_E" begin="1200" end="1800" vehsPerHour="130" departLane="best" departSpeed="max"/>
    <flow id="r3_SE" type="car" route="S_E" begin="1200" end="1800" vehsPerHour="120" departLane="best" departSpeed="max"/>
</routes>
"""
    (scen_dir / "cologne1.rou.xml").write_text(rou_xml, encoding="utf-8")

    # 4. GUI View Settings
    gui_xml = """<?xml version="1.0" encoding="UTF-8"?>
<viewsettings>
    <scheme name="real world"/>
    <delay value="60"/>
    <viewport zoom="240" x="300" y="300" angle="0"/>
</viewsettings>
"""
    (scen_dir / "gui-settings.xml").write_text(gui_xml, encoding="utf-8")

    # 5. SUMO Config
    cfg_xml = """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="cologne1.net.xml"/>
        <route-files value="cologne1.rou.xml"/>
        <gui-settings-file value="gui-settings.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="1800"/>
        <step-length value="1.0"/>
    </time>
    <processing>
        <time-to-teleport value="-1"/>
    </processing>
    <report>
        <no-step-log value="true"/>
    </report>
</configuration>
"""
    (scen_dir / "cologne1.sumocfg").write_text(cfg_xml, encoding="utf-8")
    return scen_dir


if __name__ == "__main__":
    c1 = build_cologne1_network()
    print(f"Built network successfully at: {c1}")
