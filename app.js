/**
 * TrafficRL — Akademik Vitrin & İnteraktif Simülasyon Oynatıcısı
 * Gerçek Eclipse SUMO (Cologne-3) yörünge ve benchmark verilerini görselleştirir.
 */

(function () {
  "use strict";

  const MODE_LABELS = {
    fixed: { name: "1. Sabit Süreli (Fixed-Time)", badge: "Baz Çizgi", rowClass: "" },
    actuated: { name: "2. Sensörlü (Actuated)", badge: "Klasik", rowClass: "" },
    maxpressure: { name: "3. Max-Pressure", badge: "Adaptif", rowClass: "" },
    dqn: { name: "4. Akıllı DQN RL (Bizim Model)", badge: "Önerilen", rowClass: "bg-emerald-500/10" },
  };

  const state = {
    playback: null,
    benchmark: null,
    roadLayer: null,
    frameIndex: 0,
    isPlaying: false,
    speed: 1,
    lastTs: 0,
    accumulatorMs: 0,
    baseFrameIntervalMs: 200, // 1x = 5 simülasyon saniyesi / gerçek saniye
  };

  // DOM referansları
  const el = {
    btnPlayPause: document.getElementById("btn-play-pause"),
    txtPlay: document.getElementById("txt-play"),
    btnReset: document.getElementById("btn-reset"),
    speedBtns: document.querySelectorAll(".speed-btn"),
    scrubber: document.getElementById("timeline-scrubber"),
    simClock: document.getElementById("sim-clock"),
    simTotal: document.getElementById("sim-total"),
    canvasFixed: document.getElementById("canvas-fixed"),
    canvasDqn: document.getElementById("canvas-dqn"),
    fixedQueue: document.getElementById("fixed-queue"),
    fixedCompleted: document.getElementById("fixed-completed"),
    fixedCo2: document.getElementById("fixed-co2"),
    dqnQueue: document.getElementById("dqn-queue"),
    dqnCompleted: document.getElementById("dqn-completed"),
    dqnCo2: document.getElementById("dqn-co2"),
    tbody: document.getElementById("benchmark-tbody"),
    chartBenchmark: document.getElementById("chart-benchmark"),
    chartLearning: document.getElementById("chart-learning"),
  };

  async function init() {
    bindControls();

    try {
      const [benchRes, playRes] = await Promise.all([
        fetch("data/benchmark_data.json"),
        fetch("data/playback_cologne3.json"),
      ]);

      if (!benchRes.ok || !playRes.ok) {
        throw new Error("Veri dosyaları yüklenemedi.");
      }

      const [benchData, playData] = await Promise.all([benchRes.json(), playRes.json()]);
      state.benchmark = benchData;
      state.playback = playData;

      buildRoadLayer(playData.lanes, playData.meta.width, playData.meta.height);
      if (el.simTotal && playData.meta && playData.meta.duration) {
        el.simTotal.textContent = playData.meta.duration + "s";
      }
      if (el.scrubber && playData.fixed && playData.fixed.length > 0) {
        el.scrubber.max = String(playData.fixed.length - 1);
      }

      renderBenchmarkTable(benchData.benchmark);
      renderBenchmarkChart(benchData.benchmark);
      renderLearningChart(benchData.learning_curve);
      renderFrame(0);
    } catch (err) {
      console.error("Veri yükleme hatası:", err);
      drawFallbackNotice(el.canvasFixed, err.message);
      drawFallbackNotice(el.canvasDqn, err.message);
    }
  }

  function drawFallbackNotice(canvas, msg) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#060a13";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#f43f5e";
    ctx.font = "bold 20px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Simülasyon verisi yüklenemedi (" + msg + ")", canvas.width / 2, canvas.height / 2 - 12);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "15px JetBrains Mono, monospace";
    ctx.fillText("Lütfen web/siteyi_baslat.bat ile yerel sunucudan açın.", canvas.width / 2, canvas.height / 2 + 20);
  }

  function buildRoadLayer(lanes, width, height) {
    const offscreen = document.createElement("canvas");
    offscreen.width = width;
    offscreen.height = height;
    const ctx = offscreen.getContext("2d");

    // Koyu kontrol odası arka planı
    ctx.fillStyle = "#050912";
    ctx.fillRect(0, 0, width, height);

    // İnce arka plan ızgarası
    ctx.strokeStyle = "rgba(30, 41, 59, 0.28)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x += 50) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += 50) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Şerit dış bordürleri
    for (const lane of lanes) {
      if (!lane.pts || lane.pts.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(lane.pts[0][0], lane.pts[0][1]);
      for (let i = 1; i < lane.pts.length; i++) {
        ctx.lineTo(lane.pts[i][0], lane.pts[i][1]);
      }
      ctx.strokeStyle = "#1e293b";
      ctx.lineWidth = 10;
      ctx.stroke();
    }

    // Asfalt iç yüzeyi
    for (const lane of lanes) {
      if (!lane.pts || lane.pts.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(lane.pts[0][0], lane.pts[0][1]);
      for (let i = 1; i < lane.pts.length; i++) {
        ctx.lineTo(lane.pts[i][0], lane.pts[i][1]);
      }
      ctx.strokeStyle = "#0f172a";
      ctx.lineWidth = 7;
      ctx.stroke();
    }

    // Merkez şerit çizgileri
    ctx.setLineDash([4, 6]);
    for (const lane of lanes) {
      if (!lane.pts || lane.pts.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(lane.pts[0][0], lane.pts[0][1]);
      for (let i = 1; i < lane.pts.length; i++) {
        ctx.lineTo(lane.pts[i][0], lane.pts[i][1]);
      }
      ctx.strokeStyle = "rgba(100, 116, 139, 0.25)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    ctx.setLineDash([]);

    state.roadLayer = offscreen;
  }

  function signalColor(char) {
    if (char === "G" || char === "g") return "#10b981";
    if (char === "y" || char === "Y") return "#f59e0b";
    return "#ef4444";
  }

  function drawScene(canvas, frame) {
    if (!canvas || !frame || !state.playback) return;
    const ctx = canvas.getContext("2d");

    if (state.roadLayer) {
      ctx.drawImage(state.roadLayer, 0, 0);
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    // Durma çizgisi trafik ışıkları
    const stops = state.playback.stop_points || [];
    const lightStr = frame.l || "";
    const count = Math.min(stops.length, lightStr.length);
    for (let i = 0; i < count; i++) {
      const pt = stops[i];
      const color = signalColor(lightStr[i]);

      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 4.2, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 7.5, 0, Math.PI * 2);
      ctx.fillStyle = color + "33";
      ctx.fill();
    }

    // Araçlar: [nx, ny, angle_deg, is_halted]
    const vehicles = frame.v || [];
    for (let i = 0; i < vehicles.length; i++) {
      const [vx, vy, angleDeg, halted] = vehicles[i];
      ctx.save();
      ctx.translate(vx, vy);
      ctx.rotate((angleDeg * Math.PI) / 180);

      // Gövde
      const w = 5.2;
      const h = 10.4;
      ctx.fillStyle = halted ? "#f43f5e" : "#34d399";
      ctx.beginPath();
      ctx.roundRect(-w / 2, -h / 2, w, h, 1.5);
      ctx.fill();

      // Ön cam / yön göstergesi (-Y tarafı burun)
      ctx.fillStyle = halted ? "#ffe4e6" : "#ecfdf5";
      ctx.fillRect(-w / 2 + 0.9, -h / 2 + 1.2, w - 1.8, 2.1);

      ctx.restore();
    }
  }

  function formatClock(seconds) {
    return String(seconds).padStart(3, "0") + "s";
  }

  function renderFrame(idx) {
    if (!state.playback) return;
    const maxIdx = state.playback.fixed.length - 1;
    const clamped = Math.max(0, Math.min(idx, maxIdx));
    state.frameIndex = clamped;

    const fFixed = state.playback.fixed[clamped];
    const fDqn = state.playback.dqn[clamped];

    drawScene(el.canvasFixed, fFixed);
    drawScene(el.canvasDqn, fDqn);

    // Telemetri güncellemeleri
    if (fFixed) {
      el.fixedQueue.textContent = String(fFixed.qh);
      el.fixedCompleted.textContent = String(fFixed.arrived);
      el.fixedCo2.textContent = fFixed.co2.toFixed(1) + " kg";
      el.simClock.textContent = formatClock(fFixed.t);
    }

    if (fDqn) {
      el.dqnQueue.textContent = String(fDqn.qh);
      el.dqnCompleted.textContent = String(fDqn.arrived);
      el.dqnCo2.textContent = fDqn.co2.toFixed(1) + " kg";
    }

    if (el.scrubber) {
      el.scrubber.value = String(clamped);
    }
  }

  function setPlaying(playing) {
    state.isPlaying = playing;
    if (el.txtPlay) {
      el.txtPlay.textContent = playing ? "Duraklat" : "Başlat";
    }
    const iconEl = el.btnPlayPause ? el.btnPlayPause.querySelector("svg, i") : null;
    if (iconEl && window.lucide) {
      iconEl.setAttribute("data-lucide", playing ? "pause" : "play");
      window.lucide.createIcons();
    }

    if (playing) {
      if (state.playback && state.frameIndex >= state.playback.fixed.length - 1) {
        state.frameIndex = 0;
      }
      state.lastTs = performance.now();
      state.accumulatorMs = 0;
      requestAnimationFrame(tick);
    }
  }

  function tick(ts) {
    if (!state.isPlaying || !state.playback) return;
    const dt = ts - state.lastTs;
    state.lastTs = ts;
    state.accumulatorMs += dt;

    const stepMs = state.baseFrameIntervalMs / state.speed;
    if (state.accumulatorMs >= stepMs) {
      const steps = Math.floor(state.accumulatorMs / stepMs);
      state.accumulatorMs -= steps * stepMs;
      const nextIdx = state.frameIndex + steps;

      if (nextIdx >= state.playback.fixed.length - 1) {
        renderFrame(state.playback.fixed.length - 1);
        setPlaying(false);
        return;
      }
      renderFrame(nextIdx);
    }

    requestAnimationFrame(tick);
  }

  function bindControls() {
    if (el.btnPlayPause) {
      el.btnPlayPause.addEventListener("click", () => {
        setPlaying(!state.isPlaying);
      });
    }

    if (el.btnReset) {
      el.btnReset.addEventListener("click", () => {
        setPlaying(false);
        renderFrame(0);
      });
    }

    el.speedBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const speed = Number(btn.dataset.speed) || 1;
        state.speed = speed;
        el.speedBtns.forEach((b) => {
          b.className =
            "speed-btn px-2.5 py-1 rounded text-xs font-mono text-slate-400 hover:text-white cursor-pointer";
        });
        btn.className =
          "speed-btn px-2.5 py-1 rounded text-xs font-mono bg-emerald-500/20 text-emerald-300 font-bold cursor-pointer";
      });
    });

    if (el.scrubber) {
      el.scrubber.addEventListener("input", (e) => {
        setPlaying(false);
        renderFrame(Number(e.target.value));
      });
    }
  }

  function renderBenchmarkTable(rows) {
    if (!el.tbody || !rows) return;
    el.tbody.innerHTML = rows
      .map((row) => {
        const meta = MODE_LABELS[row.mode] || { name: row.mode, badge: "", rowClass: "" };
        const isDqn = row.mode === "dqn";
        const collisions = Math.round(row.collisions_mean * 5);
        const teleports = Math.round(row.teleports_mean * 5);

        let safetyBadge = "";
        if (collisions === 0 && teleports === 0) {
          safetyBadge = `<span class="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-mono text-emerald-300">0 Kaza · 0 Teleport</span>`;
        } else {
          safetyBadge = `<span class="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2.5 py-0.5 text-xs font-mono text-amber-300">${collisions} Kaza · ${teleports} Teleport</span>`;
        }

        return `
          <tr class="${meta.rowClass} hover:bg-slate-800/40 transition">
            <td class="px-6 py-4 font-semibold ${isDqn ? "text-emerald-300" : "text-white"}">
              <div class="flex items-center gap-2">
                <span>${meta.name}</span>
                ${
                  isDqn
                    ? `<span class="rounded bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-[10px] font-mono text-emerald-300">ÖNERİLEN</span>`
                    : ""
                }
              </div>
            </td>
            <td class="px-6 py-4 font-mono ${isDqn ? "text-emerald-300 font-bold" : "text-slate-200"}">${row.wait_mean.toFixed(2)} ± ${row.wait_std.toFixed(2)}s</td>
            <td class="px-6 py-4 font-mono text-slate-300">${row.queue_mean.toFixed(2)} ± ${row.queue_std.toFixed(2)}</td>
            <td class="px-6 py-4 font-mono text-slate-300">${row.travel_mean.toFixed(2)}s</td>
            <td class="px-6 py-4 font-mono text-slate-300">${row.co2_mean.toFixed(1)} kg</td>
            <td class="px-6 py-4 font-mono ${isDqn ? "text-white font-bold" : "text-slate-300"}">${Math.round(row.completed_mean)}</td>
            <td class="px-6 py-4">${safetyBadge}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderBenchmarkChart(rows) {
    if (!el.chartBenchmark || !rows || typeof Chart === "undefined") return;

    const labels = ["Fixed-Time", "Actuated", "Max-Pressure", "DQN RL"];
    const waitMeans = rows.map((r) => r.wait_mean);
    const queueMeans = rows.map((r) => r.queue_mean);

    new Chart(el.chartBenchmark, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Ort. Bekleme Süresi (sn)",
            data: waitMeans,
            backgroundColor: [
              "rgba(244, 63, 94, 0.75)",
              "rgba(251, 146, 60, 0.75)",
              "rgba(250, 204, 21, 0.75)",
              "rgba(16, 185, 129, 0.85)",
            ],
            borderColor: ["#f43f5e", "#fb923c", "#facc15", "#10b981"],
            borderWidth: 1.5,
            borderRadius: 6,
            yAxisID: "y",
          },
          {
            label: "Ort. Koridor Kuyruğu (araç)",
            data: queueMeans,
            backgroundColor: "rgba(56, 189, 248, 0.55)",
            borderColor: "#38bdf8",
            borderWidth: 1.5,
            borderRadius: 6,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: "#cbd5e1", font: { family: "Inter", size: 12 } },
          },
        },
        scales: {
          x: {
            ticks: { color: "#94a3b8", font: { family: "JetBrains Mono", size: 11 } },
            grid: { color: "rgba(51, 65, 85, 0.35)" },
          },
          y: {
            position: "left",
            title: { display: true, text: "Bekleme (sn)", color: "#94a3b8" },
            ticks: { color: "#94a3b8" },
            grid: { color: "rgba(51, 65, 85, 0.35)" },
          },
          y1: {
            position: "right",
            title: { display: true, text: "Kuyruk (araç)", color: "#38bdf8" },
            ticks: { color: "#38bdf8" },
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
  }

  function renderLearningChart(curve) {
    if (!el.chartLearning || !curve || typeof Chart === "undefined") return;

    const labels = curve.map((c) => "Ep " + c.ep);
    const waitVals = curve.map((c) => c.wait);
    const bestVals = curve.map((c) => c.best);

    new Chart(el.chartLearning, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Bölüm Ort. Bekleme (sn)",
            data: waitVals,
            borderColor: "#38bdf8",
            backgroundColor: "rgba(56, 189, 248, 0.12)",
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.28,
            fill: true,
          },
          {
            label: "En İyi Skor İlerlemesi (Best)",
            data: bestVals,
            borderColor: "#10b981",
            borderDash: [5, 4],
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: "#cbd5e1", font: { family: "Inter", size: 12 } },
          },
        },
        scales: {
          x: {
            ticks: { color: "#94a3b8", maxTicksLimit: 10, font: { family: "JetBrains Mono", size: 11 } },
            grid: { color: "rgba(51, 65, 85, 0.3)" },
          },
          y: {
            title: { display: true, text: "Bekleme Süresi (sn)", color: "#94a3b8" },
            ticks: { color: "#94a3b8" },
            grid: { color: "rgba(51, 65, 85, 0.35)" },
          },
        },
      },
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
