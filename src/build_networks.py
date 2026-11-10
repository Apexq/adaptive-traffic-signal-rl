"""
Network Builder for Traffic-RL Benchmark Scenarios
Generates SUMO road networks (.net.xml), calibrated peak-hour traffic demand (.rou.xml),
and SUMO configurations (.sumocfg) for:
  1. cologne1: Single 4-way urban intersection benchmark (TL_C1)
  2. cologne3: 3-intersection urban arterial corridor benchmark (TL_1, TL_2, TL_3)
"""

import subprocess
from pathlib import Path

SUMO_BIN = Path(r"C:\Program Files (x86)\SUMO\bin")
NETCONVERT = SUMO_BIN / "netconvert.exe"
BASE_DIR = Path(__file__).resolve().parent.parent
NETS_DIR = BASE_DIR / "nets"


def build_cologne1_network() -> Path:
    """Builds the Cologne-1 single intersection benchmark (3-lane approaches)."""
    scen_dir = NETS_DIR / "cologne1"
    scen_dir.mkdir(parents=True, exist_ok=True)

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

    rou_xml = """<?xml version="1.0" encoding="UTF-8"?>
<routes>
    <vType id="car" vClass="passenger" guiShape="passenger" length="4.5" minGap="2.5" accel="2.6" decel="4.5" maxSpeed="15.0" color="70,180,255" emissionClass="HBEFA3/PC_G_EU4"/>
    <vType id="bus" vClass="bus" guiShape="bus" length="12.0" minGap="3.0" accel="1.5" decel="3.5" maxSpeed="12.5" color="255,180,40" emissionClass="HBEFA3/Bus"/>

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

    <!-- Regime 1 (0 - 600s): Heavy East-West Arterial Flow -->
    <flow id="r1_WE" type="car" route="W_E" begin="0" end="600" vehsPerHour="650" departLane="best" departSpeed="max"/>
    <flow id="r1_WN" type="car" route="W_N" begin="0" end="600" vehsPerHour="180" departLane="best" departSpeed="max"/>
    <flow id="r1_WS" type="car" route="W_S" begin="0" end="600" vehsPerHour="140" departLane="best" departSpeed="max"/>
    <flow id="r1_EW" type="car" route="E_W" begin="0" end="600" vehsPerHour="620" departLane="best" departSpeed="max"/>
    <flow id="r1_EN" type="car" route="E_N" begin="0" end="600" vehsPerHour="160" departLane="best" departSpeed="max"/>
    <flow id="r1_ES" type="car" route="E_S" begin="0" end="600" vehsPerHour="130" departLane="best" departSpeed="max"/>
    <flow id="r1_NS" type="car" route="N_S" begin="0" end="600" vehsPerHour="140" departLane="best" departSpeed="max"/>
    <flow id="r1_SN" type="car" route="S_N" begin="0" end="600" vehsPerHour="150" departLane="best" departSpeed="max"/>
    <flow id="r1_bus_WE" type="bus" route="W_E" begin="10" end="600" vehsPerHour="40" departLane="best" departSpeed="max"/>

    <!-- Regime 2 (600 - 1200s): Heavy North-South Commuter Surge -->
    <flow id="r2_NS" type="car" route="N_S" begin="600" end="1200" vehsPerHour="680" departLane="best" departSpeed="max"/>
    <flow id="r2_NE" type="car" route="N_E" begin="600" end="1200" vehsPerHour="190" departLane="best" departSpeed="max"/>
    <flow id="r2_NW" type="car" route="N_W" begin="600" end="1200" vehsPerHour="150" departLane="best" departSpeed="max"/>
    <flow id="r2_SN" type="car" route="S_N" begin="600" end="1200" vehsPerHour="640" departLane="best" departSpeed="max"/>
    <flow id="r2_SE" type="car" route="S_E" begin="600" end="1200" vehsPerHour="170" departLane="best" departSpeed="max"/>
    <flow id="r2_SW" type="car" route="S_W" begin="600" end="1200" vehsPerHour="140" departLane="best" departSpeed="max"/>
    <flow id="r2_WE" type="car" route="W_E" begin="600" end="1200" vehsPerHour="160" departLane="best" departSpeed="max"/>
    <flow id="r2_EW" type="car" route="E_W" begin="600" end="1200" vehsPerHour="150" departLane="best" departSpeed="max"/>
    <flow id="r2_bus_NS" type="bus" route="N_S" begin="610" end="1200" vehsPerHour="45" departLane="best" departSpeed="max"/>

    <!-- Regime 3 (1200 - 1800s): Balanced Peak Congestion -->
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

    gui_xml = """<?xml version="1.0" encoding="UTF-8"?>
<viewsettings>
    <scheme name="real world"/>
    <delay value="60"/>
    <viewport zoom="240" x="300" y="300" angle="0"/>
</viewsettings>
"""
    (scen_dir / "gui-settings.xml").write_text(gui_xml, encoding="utf-8")

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


def build_cologne3_network() -> Path:
    """
    Builds the Cologne-3 Urban Arterial Corridor Benchmark (3 Signalized Intersections: TL_1, TL_2, TL_3).
    Geometry:
      - 3 consecutive intersections along a 750m East-West arterial corridor:
        J1 (-250, 0) [TL_1] --- J2 (0, 0) [TL_2] --- J3 (250, 0) [TL_3]
      - Each intersection has North and South cross-streets (N1/S1, N2/S2, N3/S3).
    """
    scen_dir = NETS_DIR / "cologne3"
    scen_dir.mkdir(parents=True, exist_ok=True)

    nod_xml = """<?xml version="1.0" encoding="UTF-8"?>
<nodes>
    <!-- 3 Signalized Corridor Intersections -->
    <node id="J1" x="-250.0" y="0.0" type="traffic_light" tl="TL_1"/>
    <node id="J2" x="0.0"    y="0.0" type="traffic_light" tl="TL_2"/>
    <node id="J3" x="250.0"  y="0.0" type="traffic_light" tl="TL_3"/>

    <!-- West & East Corridor Endpoints -->
    <node id="W_End" x="-500.0" y="0.0" type="priority"/>
    <node id="E_End" x="500.0"  y="0.0" type="priority"/>

    <!-- Cross-Street Endpoints for J1, J2, J3 -->
    <node id="N1" x="-250.0" y="250.0"  type="priority"/>
    <node id="S1" x="-250.0" y="-250.0" type="priority"/>
    <node id="N2" x="0.0"    y="250.0"  type="priority"/>
    <node id="S2" x="0.0"    y="-250.0" type="priority"/>
    <node id="N3" x="250.0"  y="250.0"  type="priority"/>
    <node id="S3" x="250.0"  y="-250.0" type="priority"/>
</nodes>
"""
    (scen_dir / "cologne3.nod.xml").write_text(nod_xml, encoding="utf-8")

    edg_xml = """<?xml version="1.0" encoding="UTF-8"?>
<edges>
    <!-- East-West Arterial Corridor Links (2 lanes per direction) -->
    <edge id="W2J1" from="W_End" to="J1"    numLanes="2" speed="13.89" priority="3"/>
    <edge id="J12W" from="J1"    to="W_End" numLanes="2" speed="13.89" priority="3"/>

    <edge id="J12J2" from="J1" to="J2" numLanes="2" speed="13.89" priority="3"/>
    <edge id="J22J1" from="J2" to="J1" numLanes="2" speed="13.89" priority="3"/>

    <edge id="J22J3" from="J2" to="J3" numLanes="2" speed="13.89" priority="3"/>
    <edge id="J32J2" from="J3" to="J2" numLanes="2" speed="13.89" priority="3"/>

    <edge id="E2J3" from="E_End" to="J3"    numLanes="2" speed="13.89" priority="3"/>
    <edge id="J32E" from="J3"    to="E_End" numLanes="2" speed="13.89" priority="3"/>

    <!-- Cross-Streets for Intersection 1 (J1) -->
    <edge id="N12J1" from="N1" to="J1" numLanes="2" speed="13.89" priority="2"/>
    <edge id="J12N1" from="J1" to="N1" numLanes="2" speed="13.89" priority="2"/>
    <edge id="S12J1" from="S1" to="J1" numLanes="2" speed="13.89" priority="2"/>
    <edge id="J12S1" from="J1" to="S1" numLanes="2" speed="13.89" priority="2"/>

    <!-- Cross-Streets for Intersection 2 (J2) -->
    <edge id="N22J2" from="N2" to="J2" numLanes="2" speed="13.89" priority="2"/>
    <edge id="J22N2" from="J2" to="N2" numLanes="2" speed="13.89" priority="2"/>
    <edge id="S22J2" from="S2" to="J2" numLanes="2" speed="13.89" priority="2"/>
    <edge id="J22S2" from="J2" to="S2" numLanes="2" speed="13.89" priority="2"/>

    <!-- Cross-Streets for Intersection 3 (J3) -->
    <edge id="N32J3" from="N3" to="J3" numLanes="2" speed="13.89" priority="2"/>
    <edge id="J32N3" from="J3" to="N3" numLanes="2" speed="13.89" priority="2"/>
    <edge id="S32J3" from="S3" to="J3" numLanes="2" speed="13.89" priority="2"/>
    <edge id="J32S3" from="J3" to="S3" numLanes="2" speed="13.89" priority="2"/>
</edges>
"""
    (scen_dir / "cologne3.edg.xml").write_text(edg_xml, encoding="utf-8")

    net_file = scen_dir / "cologne3.net.xml"
    subprocess.run(
        [
            str(NETCONVERT),
            f"--node-files={scen_dir / 'cologne3.nod.xml'}",
            f"--edge-files={scen_dir / 'cologne3.edg.xml'}",
            f"--output-file={net_file}",
            "--no-turnarounds=true",
        ],
        check=True,
    )

    # Calibrated 3-Intersection Corridor Traffic Demand (Sorted by begin time)
    rou_xml = """<?xml version="1.0" encoding="UTF-8"?>
<routes>
    <vType id="car" vClass="passenger" guiShape="passenger" length="4.5" minGap="2.5" accel="2.6" decel="4.5" maxSpeed="15.0" color="50,190,255" emissionClass="HBEFA3/PC_G_EU4"/>
    <vType id="bus" vClass="bus" guiShape="bus" length="12.0" minGap="3.0" accel="1.5" decel="3.5" maxSpeed="12.5" color="255,165,0" emissionClass="HBEFA3/Bus"/>

    <!-- Full Corridor Arterial Routes -->
    <route id="corridor_W_E" edges="W2J1 J12J2 J22J3 J32E"/>
    <route id="corridor_E_W" edges="E2J3 J32J2 J22J1 J12W"/>

    <!-- Turning & Cross-Street Routes at J1, J2, J3 -->
    <route id="W_to_N2" edges="W2J1 J12J2 J22N2"/>
    <route id="W_to_S3" edges="W2J1 J12J2 J22J3 J32S3"/>
    <route id="E_to_S2" edges="E2J3 J32J2 J22S2"/>
    <route id="E_to_N1" edges="E2J3 J32J2 J22J1 J12N1"/>

    <route id="N1_to_S1" edges="N12J1 J12S1"/>
    <route id="S1_to_N1" edges="S12J1 J12N1"/>
    <route id="N1_to_E"  edges="N12J1 J12J2 J22J3 J32E"/>

    <route id="N2_to_S2" edges="N22J2 J22S2"/>
    <route id="S2_to_N2" edges="S22J2 J22N2"/>
    <route id="S2_to_E"  edges="S22J2 J22J3 J32E"/>

    <route id="N3_to_S3" edges="N32J3 J32S3"/>
    <route id="S3_to_N3" edges="S32J3 J32N3"/>
    <route id="N3_to_W"  edges="N32J3 J32J2 J22J1 J12W"/>

    <!-- Regime 1 (0 - 600s): Heavy East-West Arterial Wave Across All 3 Intersections -->
    <flow id="c3_r1_WE" type="car" route="corridor_W_E" begin="0" end="600" vehsPerHour="520" departLane="best" departSpeed="max"/>
    <flow id="c3_r1_EW" type="car" route="corridor_E_W" begin="0" end="600" vehsPerHour="480" departLane="best" departSpeed="max"/>
    <flow id="c3_r1_WN2" type="car" route="W_to_N2" begin="0" end="600" vehsPerHour="140" departLane="best" departSpeed="max"/>
    <flow id="c3_r1_ES2" type="car" route="E_to_S2" begin="0" end="600" vehsPerHour="130" departLane="best" departSpeed="max"/>
    <flow id="c3_r1_N1S1" type="car" route="N1_to_S1" begin="0" end="600" vehsPerHour="120" departLane="best" departSpeed="max"/>
    <flow id="c3_r1_N2S2" type="car" route="N2_to_S2" begin="0" end="600" vehsPerHour="140" departLane="best" departSpeed="max"/>
    <flow id="c3_r1_N3S3" type="car" route="N3_to_S3" begin="0" end="600" vehsPerHour="120" departLane="best" departSpeed="max"/>
    <flow id="c3_r1_bus1" type="bus" route="corridor_W_E" begin="5" end="600" vehsPerHour="40" departLane="best" departSpeed="max"/>
    <flow id="c3_r1_bus2" type="bus" route="corridor_E_W" begin="15" end="600" vehsPerHour="35" departLane="best" departSpeed="max"/>

    <!-- Regime 2 (600 - 1200s): Heavy North-South Cross-Street Surge at J1, J2, J3 -->
    <flow id="c3_r2_N1S1" type="car" route="N1_to_S1" begin="600" end="1200" vehsPerHour="420" departLane="best" departSpeed="max"/>
    <flow id="c3_r2_S1N1" type="car" route="S1_to_N1" begin="600" end="1200" vehsPerHour="380" departLane="best" departSpeed="max"/>
    <flow id="c3_r2_N2S2" type="car" route="N2_to_S2" begin="600" end="1200" vehsPerHour="460" departLane="best" departSpeed="max"/>
    <flow id="c3_r2_S2N2" type="car" route="S2_to_N2" begin="600" end="1200" vehsPerHour="440" departLane="best" departSpeed="max"/>
    <flow id="c3_r2_N3S3" type="car" route="N3_to_S3" begin="600" end="1200" vehsPerHour="400" departLane="best" departSpeed="max"/>
    <flow id="c3_r2_S3N3" type="car" route="S3_to_N3" begin="600" end="1200" vehsPerHour="390" departLane="best" departSpeed="max"/>
    <flow id="c3_r2_WE" type="car" route="corridor_W_E" begin="600" end="1200" vehsPerHour="180" departLane="best" departSpeed="max"/>
    <flow id="c3_r2_EW" type="car" route="corridor_E_W" begin="600" end="1200" vehsPerHour="170" departLane="best" departSpeed="max"/>

    <!-- Regime 3 (1200 - 1800s): Combined Corridor & Cross-Street Rush Hour -->
    <flow id="c3_r3_WE" type="car" route="corridor_W_E" begin="1200" end="1800" vehsPerHour="380" departLane="best" departSpeed="max"/>
    <flow id="c3_r3_EW" type="car" route="corridor_E_W" begin="1200" end="1800" vehsPerHour="360" departLane="best" departSpeed="max"/>
    <flow id="c3_r3_N1E" type="car" route="N1_to_E" begin="1200" end="1800" vehsPerHour="160" departLane="best" departSpeed="max"/>
    <flow id="c3_r3_S2E" type="car" route="S2_to_E" begin="1200" end="1800" vehsPerHour="150" departLane="best" departSpeed="max"/>
    <flow id="c3_r3_N3W" type="car" route="N3_to_W" begin="1200" end="1800" vehsPerHour="150" departLane="best" departSpeed="max"/>
    <flow id="c3_r3_N2S2" type="car" route="N2_to_S2" begin="1200" end="1800" vehsPerHour="280" departLane="best" departSpeed="max"/>
    <flow id="c3_r3_S1N1" type="car" route="S1_to_N1" begin="1200" end="1800" vehsPerHour="260" departLane="best" departSpeed="max"/>
</routes>
"""
    (scen_dir / "cologne3.rou.xml").write_text(rou_xml, encoding="utf-8")

    gui_xml = """<?xml version="1.0" encoding="UTF-8"?>
<viewsettings>
    <scheme name="real world"/>
    <delay value="60"/>
    <viewport zoom="140" x="500" y="250" angle="0"/>
</viewsettings>
"""
    (scen_dir / "gui-settings.xml").write_text(gui_xml, encoding="utf-8")

    cfg_xml = """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="cologne3.net.xml"/>
        <route-files value="cologne3.rou.xml"/>
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
    (scen_dir / "cologne3.sumocfg").write_text(cfg_xml, encoding="utf-8")
    return scen_dir


if __name__ == "__main__":
    c1 = build_cologne1_network()
    c3 = build_cologne3_network()
    print(f"Built Cologne-1 (1 intersection) at: {c1}")
    print(f"Built Cologne-3 (3 intersections) at: {c3}")
