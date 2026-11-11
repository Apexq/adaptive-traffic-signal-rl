"""
Generates a 2-page professional PDF (Proje_Ozeti_ve_AI_Brifingi.pdf) and Word document
(Proje_Ozeti_ve_AI_Brifingi.docx) summarizing the entire graduation project, architecture,
50-episode training results, and instructions for a collaborator's AI assistant.
"""

import os
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ==============================================================================
# PART 1: PURE PYTHON 2-PAGE VECTOR PDF GENERATOR
# ==============================================================================

# Standard PDF Base-14 Type1 fonts (Helvetica/Courier) natively include Latin-1 (cp1252)
# glyphs (including Ç, ç, Ö, ö, Ü, ü). For the 6 Turkish-specific letters outside Latin-1
# (Ğ, ğ, İ, ı, Ş, ş), we map to their Latin-1 base characters so zero letters ever disappear
# in any PDF viewer or AI parser.
TR_NORMALIZE = str.maketrans({
    "Ğ": "G",
    "ğ": "g",
    "İ": "I",
    "ı": "i",
    "Ş": "S",
    "ş": "s",
    "–": "-",
    "—": "-",
    "’": "'",
    "“": '"',
    "”": '"',
})


def pdf_escape_bytes(text: str) -> bytes:
    text = text.translate(TR_NORMALIZE)
    out = bytearray()
    for ch in text:
        try:
            b = ch.encode("cp1252")[0]
        except UnicodeEncodeError:
            b = ord("?")
        if b in (0x28, 0x29, 0x5C):  # '(', ')', '\'
            out.append(0x5C)
            out.append(b)
        elif 32 <= b <= 126:
            out.append(b)
        else:
            out.extend(f"\\{b:03o}".encode("ascii"))
    return bytes(out)


def approx_text_width(text: str, size: float, bold: bool = False) -> float:
    text = text.translate(TR_NORMALIZE)
    total = 0.0
    for ch in text:
        if ch in "ilI.,:;|!1' ":
            w = 0.28
        elif ch in "ftrj()[]-":
            w = 0.35
        elif ch in "mwMW@%":
            w = 0.82
        elif ch.isupper():
            w = 0.67 if bold else 0.64
        else:
            w = 0.54 if bold else 0.51
        total += w
    return total * size


class TwoPageCanvas:
    def __init__(self):
        self.pages = [[], []]  # 2 pages of PDF content streams
        self.page_idx = 0
        self.width = 595.28   # A4 width in pt
        self.height = 841.89  # A4 height in pt
        self.margin_x = 34.0
        self.y = self.height - 32.0

    def cmd(self, s: str):
        self.pages[self.page_idx].append(s.encode("latin1"))

    def cmd_bytes(self, b: bytes):
        self.pages[self.page_idx].append(b)

    def next_page(self):
        self.page_idx = 1
        self.y = self.height - 34.0

    def rect_fill(self, x, y, w, h, r, g, b, stroke_rgb=None):
        self.cmd(f"q {r:.3f} {g:.3f} {b:.3f} rg ")
        if stroke_rgb:
            sr, sg, sb = stroke_rgb
            self.cmd(f"{sr:.3f} {sg:.3f} {sb:.3f} RG 0.8 w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re B Q\n")
        else:
            self.cmd(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f Q\n")

    def line(self, x1, y1, x2, y2, r, g, b, width=1.0):
        self.cmd(f"q {r:.3f} {g:.3f} {b:.3f} RG {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q\n")

    def text(self, x, y, txt: str, font="F1", size=9.2, rgb=(0.12, 0.16, 0.23)):
        r, g, b = rgb
        esc = pdf_escape_bytes(txt)
        self.cmd_bytes(
            f"BT /{font} {size:.2f} Tf {r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} Td (".encode("ascii")
            + esc
            + b") Tj ET\n"
        )

    def wrap_lines(self, txt: str, max_chars: int):
        words = txt.split(" ")
        lines = []
        cur = ""
        for w in words:
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= max_chars:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def paragraph(self, txt: str, font="F1", size=8.9, rgb=(0.12, 0.16, 0.23), indent=0.0, leading=12.0, max_chars=102):
        for line in self.wrap_lines(txt, max_chars):
            self.text(self.margin_x + indent, self.y, line, font=font, size=size, rgb=rgb)
            self.y -= leading

    def bullet(self, bold_prefix: str, rest: str, indent=6.0, max_chars=96):
        full = f"{bold_prefix} {rest}".strip()
        lines = self.wrap_lines(full, max_chars)
        for i, line in enumerate(lines):
            if i == 0:
                self.text(self.margin_x + indent, self.y, "•", font="F2", size=9.2, rgb=(0.15, 0.39, 0.92))
                if bold_prefix and line.startswith(bold_prefix):
                    rem = line[len(bold_prefix):]
                    b_esc = pdf_escape_bytes(bold_prefix)
                    r_esc = pdf_escape_bytes(rem)
                    x_pos = self.margin_x + indent + 10
                    self.cmd_bytes(
                        f"BT /F2 8.65 Tf 0.060 0.090 0.160 rg {x_pos:.2f} {self.y:.2f} Td (".encode("ascii")
                        + b_esc
                        + b") Tj /F1 8.65 Tf 0.120 0.160 0.230 rg ("
                        + r_esc
                        + b") Tj ET\n"
                    )
                else:
                    self.text(self.margin_x + indent + 10, self.y, line, font="F1", size=8.65, rgb=(0.12, 0.16, 0.23))
            else:
                self.text(self.margin_x + indent + 10, self.y, line, font="F1", size=8.65, rgb=(0.12, 0.16, 0.23))
            self.y -= 11.8

    def section_header(self, title: str):
        self.y -= 4
        self.text(self.margin_x, self.y, title, font="F2", size=10.2, rgb=(0.06, 0.09, 0.16))
        self.y -= 4
        self.line(self.margin_x, self.y, self.width - self.margin_x, self.y, 0.15, 0.39, 0.92, width=1.4)
        self.y -= 11


def build_two_page_pdf(out_path: str):
    c = TwoPageCanvas()
    W = c.width - 2 * c.margin_x

    # ==================== PAGE 1 ====================
    banner_h = 46
    banner_y = c.y - banner_h + 10
    c.rect_fill(c.margin_x, banner_y, W, banner_h, 0.06, 0.09, 0.20)
    c.text(c.margin_x + 12, banner_y + 27, "PROJE TEKNIK ÖZETI VE YAPAY ZEKA (AI) BAGLAM BRIFINGI", font="F2", size=12.5, rgb=(1, 1, 1))
    c.text(c.margin_x + 12, banner_y + 11, "Simulation-Based Intelligent Traffic Management System Using Deep Reinforcement Learning (MCBÜ Bitirme Projesi)", font="F1", size=8.6, rgb=(0.82, 0.88, 0.98))
    c.y = banner_y - 8

    # Meta Box
    meta_h = 34
    meta_y = c.y - meta_h
    c.rect_fill(c.margin_x, meta_y, W, meta_h, 0.96, 0.97, 0.99, stroke_rgb=(0.75, 0.81, 0.88))
    c.text(c.margin_x + 8, meta_y + 20, "GitHub Repo: https://github.com/Apexq/adaptive-traffic-signal-rl.git (main branch - 50 epizot egitilmis model pushlu)", font="F2", size=8.4, rgb=(0.06, 0.09, 0.16))
    c.text(c.margin_x + 8, meta_y + 7, "Teknoloji: Eclipse SUMO 1.28.0 + Python 3.14 (TraCI & sumolib)  |  Veri Seti: NeurIPS 2021 RESCO (Köln, Almanya)", font="F1", size=8.4, rgb=(0.20, 0.25, 0.33))
    c.y = meta_y - 10

    # Section 1
    c.section_header("1. GERÇEK DÜNYA HARITASI VE VERI SETI (NEURIPS 2021 RESCO BENCHMARK)")
    c.paragraph(
        "Yapay izgara (grid) harita yerine, akademik literatürde standart benchmark kabul edilen NeurIPS 2021 RESCO veri setindeki gerçek Almanya / Köln (Cologne) haritasi ve gerçek sabah zirve saati (07:00-08:00, 25200-28800 sn) araç rotalari kullanilmistir:",
        size=8.8, leading=11.5, max_chars=104
    )
    c.bullet("Gerçek Konum:", "Köln-Lindenthal (50931, Köln Üniversitesi ve Üniversite Hastanesi bölgesi), Dürener Strasse ana bulvari.")
    c.bullet("1. Bati Kavsagi (Node 359566):", "Dürener Strasse & Lindenthalgürtel / Stadtwaldgürtel (50.927831, 6.908958) - Bulvar & tramvay kesisimi.")
    c.bullet("2. Orta Kavsak (Node 360086):", "Dürener Strasse & Theresienstrasse / Klosterstrasse (50.929489, 6.913100) - Ara toplayici cadde.")
    c.bullet("3. Dogu Kavsagi (Node 360082):", "Dürener Strasse & Geibelstrasse / Herbert-Lewin-Strasse (50.930924, 6.916756) - Hastane girisi.")
    c.bullet("Tekil Kavsak (nets/cologne1):", "Dürener Strasse & Universitätsstrasse (Node 357187, 50.930968, 6.926376).")

    # Section 2
    c.section_header("2. SISTEM MIMARISI VE ALGORITMIK TASARIM (NELER YAPILDI?)")
    c.bullet(
        "A. Dinamik Topoloji Kesfi & Güvenlik Kisitlari (src/corridor3_runner.py):",
        "RealNetworkSimulation sinifi haritadaki kavsaklari, gelen seritleri ve yesil fazlari XML'den otomatik kesfeder. Trafik güvenligi geregi faz degisimlerinde 3 sn sari isik (yellow_time=3s) zorunludur. Ana fazlar (Faz 0, 4) için min_green=10s, max_green=45s; sola dönüs fazlari (Faz 2, 6) için min_green=4s, max_green=12s uygulanir."
    )
    c.bullet(
        "B. 4 Fazli Akilli Faz Atlama (Acyclic 4-Phase Smart Phase Skipping):",
        "Klasik Sabit Süreli (Fixed-Time) ve Klasik Sensörlü (Actuated) sistemler fazlari sabit sirayla (0 -> 2 -> 4 -> 6) döner; sola dönecek araç olmasa bile Faz 2 ve Faz 6 için döngü basina 14 sn bosa harcanir. Bizim DQN ajanimiz ise 4 fazin tamamini degerlendirir; sola dönüs seritlerinde bekleyen araç sayisi < 2 ise valid_mask ile o fazlari atlar ve dogrudan yogun Faz 0 <-> Faz 4 arasinda geçis yapar."
    )
    c.bullet(
        "C. Faz-Rekabetli Derin Q-Agi (DeepPhaseMLP & DQNAgent - src/rl_agent.py):",
        "Her aday yesil faz p in {0,2,4,6} için 6 normalize öznitelik çikarilir: [norm_halted, norm_max_wait, norm_veh, is_current_phase, norm_green_elapsed, other_halted_pressure]. Sinir agi 6 -> 64 (ReLU) -> 64 (ReLU) -> 1 (Linear Q-Value) mimarisinde 961 parametreli çok katmanli algilayicidir (%100 rastgele He Normal ilklendirme ile sifirdan egitildi)."
    )
    c.bullet(
        "D. Ödül Fonksiyonu & Egitim Hiperparametreleri:",
        "R_t = -(0.50*(total_halted/40) + 0.35*(max_wait/120) + 0.15*is_switched). Replay Buffer N=20,000, batch_size=64, gamma=0.95, lr=0.0015, Target Network senkronizasyonu=250 adim, epsilon=1.00 -> 0.03."
    )

    # Section 3
    c.section_header("3. 50 EPIZOT EGITIM YAKINSAMASI VE 3 MODLU BENCHMARK SONUÇLARI")
    c.paragraph(
        "Model, gerçek Köln 3'lü koridorunda (cologne3) 50 tam epizot (50 x 3600 sn = 50 saatlik trafik akisi) boyunca egitilmistir (results/training_log.csv):",
        size=8.8, leading=11.5
    )
    c.bullet("Epizot 2 (Baslangiç):", "Ortalama Bekleme = 23.37 sn  |  Ortalama Kuyruk = 12.63 araç  |  TD Loss = 0.9571")
    c.bullet("Epizot 44 (En Iyi Rekor):", "Ortalama Bekleme = 8.67 sn   |  Ortalama Kuyruk = 6.20 araç   |  (models/dqn_resco_cologne.json olarak kaydedildi)")
    c.bullet("Epizot 50 (Final):", "Ortalama Bekleme = 11.61 sn  |  Ortalama Kuyruk = 7.07 araç   |  TD Loss = 0.0665 (Epsilon = 0.03)")

    c.y -= 3
    # Benchmark Table
    col_x = [c.margin_x, c.margin_x + 200, c.margin_x + 285, c.margin_x + 365, c.margin_x + 445]
    row_h = 18
    # Header row
    c.rect_fill(c.margin_x, c.y - row_h, W, row_h, 0.12, 0.16, 0.25)
    c.text(col_x[0] + 6, c.y - 12.5, "Kontrol Modu (Cologne-3, 1800s Test, seed=42)", font="F2", size=8.2, rgb=(1, 1, 1))
    c.text(col_x[1] + 6, c.y - 12.5, "Ort. Bekleme", font="F2", size=8.2, rgb=(1, 1, 1))
    c.text(col_x[2] + 6, c.y - 12.5, "Ort. Kuyruk", font="F2", size=8.2, rgb=(1, 1, 1))
    c.text(col_x[3] + 6, c.y - 12.5, "Seyahat Süresi", font="F2", size=8.2, rgb=(1, 1, 1))
    c.text(col_x[4] + 6, c.y - 12.5, "CO2 Salinimi", font="F2", size=8.2, rgb=(1, 1, 1))
    c.y -= row_h

    rows = [
        ("1. Fixed-Time (Sabit Süreli Klasik)", "33.09 sn", "18.34 araç", "82.88 sn", "91.86 kg", False),
        ("2. Actuated (Klasik Sirali Sensörlü)", "31.00 sn (-%6.3)", "14.02 araç", "83.17 sn", "82.80 kg", False),
        ("3. DQN RL (4 Fazli Akilli Faz Atlama)", "14.40 sn (-%56.5)", "7.30 araç (-%60.2)", "62.77 sn (-%24.3)", "54.80 kg (-%40.3)", True),
    ]
    for r_idx, (m_name, w_val, q_val, t_val, co2_val, is_hl) in enumerate(rows):
        bg = (0.88, 0.98, 0.93) if is_hl else ((0.97, 0.98, 1.0) if r_idx % 2 == 0 else (1.0, 1.0, 1.0))
        fg = (0.02, 0.35, 0.25) if is_hl else (0.12, 0.16, 0.23)
        fnt = "F2" if is_hl else "F1"
        c.rect_fill(c.margin_x, c.y - row_h, W, row_h, *bg, stroke_rgb=(0.75, 0.81, 0.88))
        c.text(col_x[0] + 6, c.y - 12.5, m_name, font=fnt, size=8.2, rgb=fg)
        c.text(col_x[1] + 6, c.y - 12.5, w_val, font=fnt, size=8.2, rgb=fg)
        c.text(col_x[2] + 6, c.y - 12.5, q_val, font=fnt, size=8.2, rgb=fg)
        c.text(col_x[3] + 6, c.y - 12.5, t_val, font=fnt, size=8.2, rgb=fg)
        c.text(col_x[4] + 6, c.y - 12.5, co2_val, font=fnt, size=8.2, rgb=fg)
        c.y -= row_h

    c.y -= 8
    # Highlight Box
    hl_h = 26
    c.rect_fill(c.margin_x, c.y - hl_h, W, hl_h, 0.88, 0.98, 0.93, stroke_rgb=(0.06, 0.65, 0.45))
    c.text(c.margin_x + 8, c.y - 16, "TEMEL BULGU: Egitilmis DQN modeli, Sabit Süreli sisteme göre bekleme süresini %56.5, Klasik Sensörlü sisteme göre %53.5 azaltmistir!", font="F2", size=7.85, rgb=(0.02, 0.35, 0.25))
    c.text(c.margin_x, 18, "Sayfa 1 / 2  -  MCBÜ Bilgisayar Mühendisligi Bitirme Projesi Teknik Özeti", font="F1", size=7.8, rgb=(0.45, 0.50, 0.58))

    # ==================== PAGE 2 ====================
    c.next_page()

    # Section 4: Repo Structure
    c.section_header("4. DEPO (REPOSITORY) DOSYA YAPISI VE ÖNEMLI MODÜLLER")
    code_lines = [
        "adaptive-traffic-signal-rl/",
        "  +-- src/rl_agent.py                  # DeepPhaseMLP (6->64->64->1), DQNAgent, ReplayBuffer, save/load & checkpoint",
        "  +-- src/corridor3_runner.py          # RealNetworkSimulation, 4 fazli akilli faz atlama, 3 modlu benchmark & egitim",
        "  +-- src/baseline_runner.py           # Tekil kavsak (cologne1) test ve karsilastirma kosucusu",
        "  +-- src/update_charts_and_report.py  # Egitim loglarindan SVG grafiklerini (learning_curve, comparison) ureten betik",
        "  +-- models/dqn_resco_cologne.json    # 50 epizot egitilmis en iyi (best) sinir agi agirliklari (production model)",
        "  +-- models/training_checkpoint.json  # Yarida birakip devam etme (resume) icin tam egitim checkpoint dosyasi",
        "  +-- nets/cologne3/ & nets/cologne1/  # Gercek Koln haritalari (.net.xml, .rou.xml, .sumocfg, gui-settings.xml)",
        "  +-- results/training_log.csv         # 50 epizotluk egitim gecmisi (episode, avg_wait_s, avg_queue, loss, epsilon)",
        "  +-- results/cologne3_corridor_summary.csv # 3 modun resmi karsilastirma metrikleri tablosu",
        "  +-- results/learning_curve.svg & cologne3_comparison.svg # Vize raporunda kullanilan egitim ve kiyaslama grafikleri",
        "  +-- docs/MCBU_Midterm_Report.docx    # MCBU resmi vize raporu formatinda doldurulmus Ingilizce rapor",
        "  +-- 1_Mod_... .bat - 6_Egitimi_... .bat # Tek tikla SUMO-GUI izleme, tablo alma ve egitim baslatma kisayollari",
    ]
    box_h = len(code_lines) * 11.5 + 12
    c.rect_fill(c.margin_x, c.y - box_h + 6, W, box_h, 0.08, 0.11, 0.18, stroke_rgb=(0.25, 0.32, 0.45))
    cy = c.y - 7
    for cl in code_lines:
        c.text(c.margin_x + 8, cy, cl, font="F3", size=7.1, rgb=(0.90, 0.94, 1.0))
        cy -= 11.5
    c.y = cy - 8

    # Section 5: How to Run
    c.section_header("5. HIZLI ÇALISTIRMA KOMUTLARI (WINDOWS .BAT VE CLI)")
    c.bullet("3 Modu Hizlica Test Edip Tablo Almak (Headless - 20 sn):", "4_Tum_Modlari_Hizli_Karsilastir_Tablo.bat  veya  python src/corridor3_runner.py --mode compare --steps 1800")
    c.bullet("SUMO-GUI'de 3 Modu Görsel Olarak Izlemek:", "1_Mod_Sabit_Sureli_3Kavsak_Izle.bat  |  2_Mod_Sensorlu_Actuated_3Kavsak_Izle.bat  |  3_Mod_Akilli_RL_DQN_3Kavsak_Izle.bat")
    c.bullet("Egitime Devam Etmek veya Sifirdan Baslatmak:", "5_Egitimi_Baslat_veya_Devam_Et.bat (Checkpoint'ten devam eder)  |  6_Egitimi_Sifirla_Bastan_Baslat.bat")

    # Section 6: Instructions for Friend's AI Assistant
    c.section_header("6. ARKADASIN YAPAY ZEKA ARACI IÇIN BAGLAM VE FINAL GÖREVLERI (AI PROMPT REHBERI)")
    info_h = 34
    c.rect_fill(c.margin_x, c.y - info_h + 6, W, info_h, 0.92, 0.95, 1.0, stroke_rgb=(0.15, 0.39, 0.92))
    c.text(c.margin_x + 8, c.y - 7, "BU DOKÜMANI OKUYAN YAPAY ZEKA ASISTANINA NOT (INSTRUCTIONS FOR COLLABORATING AI):", font="F2", size=8.4, rgb=(0.10, 0.24, 0.65))
    c.text(c.margin_x + 8, c.y - 19, "Bu proje MCBÜ Bilgisayar Müh. Bitirme Projesidir. Vize (Midterm) asamasi %100 tamamlanmis ve GitHub'a pushlanmistir.", font="F1", size=8.3, rgb=(0.12, 0.16, 0.23))
    c.y -= (info_h + 6)

    c.paragraph(
        "Mevcut çalisan çekirdek dosyalari (src/rl_agent.py, src/corridor3_runner.py ve models/dqn_resco_cologne.json) bozmadan, Final (Haziran) asamasi için asagidaki 3 modül üzerinde ekipçe gelistirme yapilabilir:",
        size=8.8, leading=11.5
    )
    c.bullet(
        "Modül 1 - Multi-Agent Komsu Kavsak Haberlesmesi (Yesil Dalga / Green Wave):",
        "Su an cologne3 içindeki 3 kavsak (359566, 360086, 360082) ayni egitilmis DeepPhaseMLP agirliklarini paylasmakta (Parameter Sharing) ancak birbirlerinin anlik kuyruk ve aktif faz bilgisini girdi olarak almamaktadir. Final asamasinda komsu kavsaktan gelen araç baskisi (upstream/downstream platoon pressure) extract_phase_features fonksiyonuna eklenerek yesil dalga koordinasyonu saglanacaktir."
    )
    c.bullet(
        "Modül 2 - Acil Durum Araci Önceligi (Emergency Vehicle Preemption - EVP):",
        "Trafige ambulans/itfaiye (vType='emergency') eklendiginde, TraCI ile gelen seritte acil durum araci algilanirsa güvenlik kisitlarini (min_green ve 3 sn sari isik) ihlal etmeden ilgili fazin öncelikli olarak yesile açilmasi (preemption override) saglanacaktir."
    )
    c.bullet(
        "Modül 3 - Canli Performans ve Karsilastirma Dashboard'u:",
        "results/training_log.csv ve results/cologne3_corridor_summary.csv çiktilari ile canli TraCI telemetri verilerini görsellestiren interaktif bir arayüz (Streamlit veya Web Dashboard) eklenecektir."
    )

    # Section 7: Technical Verification Summary
    c.section_header("7. TEKNIK DOGRULAMA ÖZETI (NEDEN SISTEM GERÇEKÇI VE AKADEMIK OLARAK SAGLAM?)")
    c.bullet(
        "Adil ve Birebir Ayni Test Ortami (Zero Cheat):",
        "Üç kontrol modu da (Fixed-Time, Actuated, DQN RL) birebir ayni cologne3.rou.xml araç rotalari ve ayni seed=42 ile kosulmaktadir. Kuyruk, bekleme süresi ve CO2 verileri dogrudan SUMO TraCI API'sinden (getLastStepHaltingNumber, getWaitingTime, getCO2Emission) saniye saniye ölçülmektedir."
    )
    c.bullet(
        "Gerçek Sinir Agi Egitimi:",
        "models/dqn_resco_cologne.json içindeki agirliklar %100 rastgele baslatilip 50 saatlik simülasyon verisi üzerinde Bellman hata geri yayilimi (backpropagation) ile egitilmistir."
    )

    c.text(c.margin_x, 18, "Sayfa 2 / 2  -  GitHub: https://github.com/Apexq/adaptive-traffic-signal-rl.git", font="F1", size=7.8, rgb=(0.45, 0.50, 0.58))

    # ==================== ASSEMBLE VALID PDF 1.4 FILE ====================
    s1 = b"".join(c.pages[0])
    s2 = b"".join(c.pages[1])

    objs = {}
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>"
    objs[3] = (
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {c.width:.2f} {c.height:.2f}] "
        f"/Resources << /Font << /F1 7 0 R /F2 8 0 R /F3 9 0 R >> >> /Contents 5 0 R >>"
    ).encode("ascii")
    objs[4] = (
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {c.width:.2f} {c.height:.2f}] "
        f"/Resources << /Font << /F1 7 0 R /F2 8 0 R /F3 9 0 R >> >> /Contents 6 0 R >>"
    ).encode("ascii")
    objs[5] = f"<< /Length {len(s1)} >>\nstream\n".encode("ascii") + s1 + b"endstream"
    objs[6] = f"<< /Length {len(s2)} >>\nstream\n".encode("ascii") + s2 + b"endstream"
    objs[7] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    objs[8] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"
    objs[9] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>"

    pdf_bytes = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for idx in range(1, 10):
        offsets[idx] = len(pdf_bytes)
        pdf_bytes.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf_bytes.extend(objs[idx])
        pdf_bytes.extend(b"\nendobj\n")

    xref_pos = len(pdf_bytes)
    pdf_bytes.extend(b"xref\n0 10\n0000000000 65535 f \n")
    for idx in range(1, 10):
        pdf_bytes.extend(f"{offsets[idx]:010d} 00000 n \n".encode("ascii"))
    pdf_bytes.extend(
        f"trailer\n<< /Size 10 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )

    with open(out_path, "wb") as f:
        f.write(pdf_bytes)


# ==============================================================================
# PART 2: WORD (.DOCX) GENERATOR FOR EASY EDITING / SHARING
# ==============================================================================

def build_docx(out_path: str):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.6)
        section.right_margin = Inches(0.6)

    title = doc.add_heading("PROJE TEKNİK ÖZETİ VE YAPAY ZEKA (AI) BAĞLAM BRİFİNGİ", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p_meta = doc.add_paragraph()
    p_meta.add_run("Proje Adı: ").bold = True
    p_meta.add_run("Simulation-Based Intelligent Traffic Management System Using Deep Reinforcement Learning (MCBÜ Bilgisayar Müh. Bitirme Projesi)\n")
    p_meta.add_run("GitHub Deposu: ").bold = True
    p_meta.add_run("https://github.com/Apexq/adaptive-traffic-signal-rl.git (main branch — 50 epizot eğitilmiş model ağırlıkları pushlu)\n")
    p_meta.add_run("Teknoloji Yığını: ").bold = True
    p_meta.add_run("Eclipse SUMO 1.28.0 + Python 3.14 (TraCI & sumolib) + Sıfırdan Eğitilmiş 4 Fazlı DeepPhaseMLP (DQN)")

    doc.add_heading("1. Gerçek Dünya Haritası ve Veri Seti (NeurIPS 2021 RESCO Benchmark)", level=2)
    doc.add_paragraph(
        "Yapay ızgara (grid) harita yerine, akademik literatürde standart kabul edilen NeurIPS 2021 RESCO veri setindeki gerçek Almanya / Köln (Cologne-Lindenthal, 50931) haritası ve sabah zirve saati (07:00-08:00, 25200-28800 sn) gerçek araç rotaları kullanılmıştır:"
    )
    items_1 = [
        ("Batı Kavşağı (359566): ", "Dürener Straße & Lindenthalgürtel / Stadtwaldgürtel (50.927831, 6.908958)"),
        ("Orta Kavşak (360086): ", "Dürener Straße & Theresienstraße / Klosterstraße (50.929489, 6.913100)"),
        ("Doğu Kavşağı (360082): ", "Dürener Straße & Geibelstraße / Herbert-Lewin-Straße (50.930924, 6.916756)"),
        ("Tekil Kavşak (cologne1 - 357187): ", "Dürener Straße & Universitätsstraße (50.930968, 6.926376)"),
    ]
    for b_txt, n_txt in items_1:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(b_txt).bold = True
        p.add_run(n_txt)

    doc.add_heading("2. Sistem Mimarisi ve Algoritmik Tasarım", level=2)
    items_2 = [
        ("Dinamik Topoloji & Güvenlik Kısıtları (src/corridor3_runner.py): ",
         "Faz değişimlerinde 3 sn sarı ışık (yellow_time=3s) zorunludur. Ana fazlar (Faz 0, 4) için min_green=10s, max_green=45s; korumalı sola dönüş fazları (Faz 2, 6) için min_green=4s, max_green=12s uygulanır."),
        ("4 Fazlı Akıllı Faz Atlama (Smart Phase Skipping): ",
         "Klasik Sabit Süreli ve Klasik Sensörlü sistemler fazları sabit sırayla (0->2->4->6) döner. Bizim DQN ajanımız ise sola dönüş şeritlerinde bekleyen araç sayısı < 2 olduğunda valid_mask ile Faz 2 ve Faz 6'yı atlar ve doğrudan yoğun Faz 0 <-> Faz 4 arasında geçiş yapar."),
        ("Faz-Rekabetli Derin Q-Ağı (DeepPhaseMLP - src/rl_agent.py): ",
         "Her yeşil faz için 6 normalize öznitelik çıkarılır: [norm_halted, norm_max_wait, norm_veh, is_current_phase, norm_green_elapsed, other_halted_pressure]. Sinir ağı 6 -> 64 (ReLU) -> 64 (ReLU) -> 1 mimarisinde 961 parametreli çok katmanlı algılayıcıdır."),
    ]
    for b_txt, n_txt in items_2:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(b_txt).bold = True
        p.add_run(n_txt)

    doc.add_heading("3. 50 Epizot Eğitim ve 3 Modlu Benchmark Sonuçları", level=2)
    doc.add_paragraph(
        "Model, cologne3 koridorunda 50 tam saatlik (50 x 3600 sn) simülasyon boyunca eğitilmiş, bekleme süresi Epizot 2'de 23.37 sn iken Epizot 44'te 8.67 sn rekoruna yakınsamıştır. 1800 sn zirve testi (seed=42) sonuçları:"
    )
    table = doc.add_table(rows=4, cols=5)
    table.style = "Table Grid"
    headers = ["Kontrol Modu", "Ort. Bekleme", "Ort. Kuyruk", "Seyahat Süresi", "CO2 Salınımı"]
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    t_rows = [
        ["1. Fixed-Time (Sabit Süreli)", "33.09 sn", "18.34 araç", "82.88 sn", "91.86 kg"],
        ["2. Actuated (Klasik Sıralı Sensörlü)", "31.00 sn (-%6.3)", "14.02 araç", "83.17 sn", "82.80 kg"],
        ["3. DQN RL (4 Fazlı Akıllı Faz Atlama)", "14.40 sn (-%56.5)", "7.30 araç (-%60.2)", "62.77 sn (-%24.3)", "54.80 kg (-%40.3)"],
    ]
    for r_i, r_data in enumerate(t_rows, start=1):
        for c_i, val in enumerate(r_data):
            table.rows[r_i].cells[c_i].text = val

    doc.add_heading("4. Arkadaşın Yapay Zeka Aracı İçin Final Aşaması Görevleri", level=2)
    items_4 = [
        ("Modül 1 - Multi-Agent Komşu Kavşak Haberleşmesi (Yeşil Dalga): ",
         "359566, 360086 ve 360082 kavşaklarının birbirine yaklaşan araç kuyruklarını (platoon pressure) durum vektörüne eklemek."),
        ("Modül 2 - Acil Durum Aracı Önceliği (Emergency Vehicle Preemption): ",
         "Ambulans/itfaiye algılandığında güvenli sarı ışık geçişiyle ilgili koridoru yeşile açmak."),
        ("Modül 3 - Canlı Karşılaştırma Dashboard'u: ",
         "results/ altındaki CSV verilerini ve canlı simülasyon metriklerini görselleştiren bir arayüz hazırlamak."),
    ]
    for b_txt, n_txt in items_4:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(b_txt).bold = True
        p.add_run(n_txt)

    doc.save(out_path)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(base_dir, "Proje_Ozeti_ve_AI_Brifingi.pdf")
    docx_path = os.path.join(base_dir, "Proje_Ozeti_ve_AI_Brifingi.docx")
    build_two_page_pdf(pdf_path)
    build_docx(docx_path)
    print(f"[OK] Generated PDF: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
    print(f"[OK] Generated DOCX: {docx_path} ({os.path.getsize(docx_path)} bytes)")
