# PROJE TEKNİK ÖZETİ VE YAPAY ZEKA (AI) BAĞLAM BRİFİNGİ

**Proje Adı:** Simulation-Based Intelligent Traffic Management System Using Deep Reinforcement Learning  
**Kurum / Bölüm:** Manisa Celal Bayar Üniversitesi (MCBÜ) – Bilgisayar Mühendisliği Bitirme Projesi  
**GitHub Deposu:** `https://github.com/Apexq/adaptive-traffic-signal-rl.git` (Branch: `main` — Eğitilmiş 50-epizot model ağırlıkları, grafikler ve vize raporu pushlanmış durumdadır)  
**Mevcut Durum:** Vize (Midterm) hedefleri %100 tamamlanmış, gerçek dünya haritası üzerinde 50 epizotluk eğitim ve 3 modlu karşılaştırma testleri doğrulanmıştır.

---

## 1. Gerçek Dünya Haritası ve Veri Seti (NeurIPS 2021 RESCO Benchmark)
Yapay ızgara (grid) haritalar yerine, akademik literatürde standart kabul edilen **NeurIPS 2021 RESCO (Reinforcement Learning Benchmarks for Traffic Signal Control)** veri setindeki gerçek **Almanya / Köln (Cologne)** haritası ve gerçek sabah zirve saati (07:00–08:00, `25200–28800 sn`) trafik talebi kullanılmıştır:
* **Bölge:** Köln-Lindenthal (Posta Kodu: 50931, Köln Üniversitesi kampüs bölgesi), **Dürener Straße** ana bulvarı.
* **`nets/cologne3/` (Ana Koridor - 3 Ardışık Kavşak):**
  1. **Batı Kavşağı (`359566`):** *Dürener Straße & Lindenthalgürtel / Stadtwaldgürtel* (`50.9278317, 6.9089588`) — Çift yönlü tramvay hattı ve bulvar kesişimi.
  2. **Orta Kavşak (`360086`):** *Dürener Straße & Theresienstraße / Klosterstraße* (`50.9294896, 6.9131000`) — Ara toplayıcı cadde kesişimi.
  3. **Doğu Kavşağı (`360082`):** *Dürener Straße & Geibelstraße / Herbert-Lewin-Straße* (`50.9309244, 6.9167566`) — Üniversite Hastanesi giriş koridoru.
* **`nets/cologne1/` (Tekil Kavşak):** *Dürener Straße & Universitätsstraße* (`357187`, `50.9309684, 6.9263762`).

---

## 2. Sistem Mimarisi ve Algoritmik Tasarım (Neler Yapıldı?)

### A. Dinamik Topoloji Keşfi ve Güvenlik Durum Makinesi (`src/corridor3_runner.py`)
* `RealNetworkSimulation` sınıfı, `sumolib` ve `TraCI` kullanarak herhangi bir gerçek SUMO haritasındaki sinyalize kavşakları, gelen şeritleri (`incoming lanes`) ve 4 yeşil fazı (`Faz 0, 2, 4, 6`) kod değiştirmeden otomatik keşfeder.
* **Güvenlik Kısıtları (Safety Constraints):** Gerçek trafik mühendisliği kuralları gereği ajan her saniye ışık değiştiremez:
  * **Zorunlu Sarı Işık (`yellow_time = 3 sn`):** Yeşil fazdan diğerine geçerken ilgili ara sarı faz (`Faz 1, 3, 5, 7`) 3 saniye boyunca zorunlu uygulanır.
  * **Minimum Yeşil Süreler:** Ana cadde ve yan cadde düz geçiş fazları (`Faz 0, 4`) için `min_green_major = 10 sn`; korumalı sola dönüş fazları (`Faz 2, 6`) için `min_green_turn = 4 sn`.
  * **Maksimum Yeşil Süreler (Starvation Önleme):** Ana fazlar için `max_green_major = 45 sn`, sola dönüş fazları için `max_green_turn = 12 sn`.

### B. 4 Fazlı Akıllı Faz Atlama (Acyclic 4-Phase Smart Phase Skipping)
* **Klasik Sistemlerin Sorunu:** Hem Sabit Süreli (`Fixed-Time`) hem de Klasik Sensörlü (`Actuated`) sistemler fazları sabit sırayla (`Faz 0 -> Faz 2 -> Faz 4 -> Faz 6`) döner. Sola dönecek araç olmasa bile `Faz 2` ve `Faz 6` için 4'er saniye yeşil + 3'er saniye sarı ışık (döngü başına 14 sn) boşa harcanır.
* **Bizim DQN Çözümümüz:** Ajan her karar anında 4 yeşil fazın tamamını değerlendirir (`action_dim = 4`). Korumalı sola dönüş şeritlerinde bekleyen araç sayısı 2'nin altındaysa (`halted < 2`), `valid_mask` mekanizması ile o sola dönüş fazı maskelenir ve ajan doğrudan `Faz 0 <-> Faz 4` arasında geçiş yapar. Sola dönüş cebinde kuyruk biriktiğinde (`halted >= 2`) ise ajan ilgili sola dönüş fazını dinamik olarak açar.

### C. Faz-Rekabetli Derin Q-Ağı (`DeepPhaseMLP` & `DQNAgent` — `src/rl_agent.py`)
* **Durum Temsili (Phase-Centric State, $x_p \in \mathbb{R}^6$):** Her aday yeşil faz $p \in \{0, 2, 4, 6\}$ için 6 normalize öznitelik çıkarılır:
  1. `norm_halted`: Fazın kontrol ettiği şeritlerde duran araç sayısı ($\min(\text{halted}/25, 1.0)$)
  2. `norm_max_wait`: Fazdaki maksimum araç bekleme süresi ($\min(\text{wait}/120, 1.0)$)
  3. `norm_veh`: Fazdaki toplam yaklaşan araç sayısı ($\min(\text{veh}/40, 1.0)$)
  4. `is_current_phase`: Faz şu an yeşil mi? ($\{0.0, 1.0\}$)
  5. `norm_green_elapsed`: Mevcut fazın ne kadar süredir yeşil olduğu ($\min(\text{elapsed}/45, 1.0)$)
  6. `other_halted_pressure`: Rakip fazlarda bekleyen toplam araç baskısı ($\min(\text{other\_halted}/35, 1.0)$)
* **Sinir Ağı Mimarisi (`DeepPhaseMLP`):** `6 -> 64 (ReLU) -> 64 (ReLU) -> 1 (Linear Q-Değeri)` yapısında, 961 eğitilebilir parametreye sahip çok katmanlı algılayıcı. %100 rastgele *He Normal* ağırlıklarla sıfırdan başlatılmıştır.
* **Ödül Fonksiyonu (Reward):**
  $$R_t = -\left(0.50 \cdot \frac{\text{total\_halted}}{40.0} + 0.35 \cdot \frac{\text{max\_wait}}{120.0} + 0.15 \cdot \mathbb{I}(\text{phase\_switched})\right)$$
* **Eğitim Hiperparametreleri:** Replay Buffer `N = 20,000`, `batch_size = 64`, $\gamma = 0.95$, öğrenme oranı $\eta = 0.0015$, Target Network güncelleme sıklığı `250 adım`, $\epsilon$-greedy (`1.00 -> 0.03`).

---

## 3. Eğitim Yakınsaması ve 3 Modlu Benchmark Sonuçları

Model, `cologne3` (3 kavşaklı gerçek Köln koridoru) üzerinde **50 tam epizot (50 x 3600 sn = 50 saatlik trafik akışı)** boyunca eğitilmiştir (`results/training_log.csv`):
* **Epizot 2:** Ort. Bekleme = `23.37 sn`, Ort. Kuyruk = `12.63 araç`, TD Loss = `0.9571`
* **Epizot 44 (En İyi Rekor):** Ort. Bekleme = **`8.67 sn`**, Ort. Kuyruk = **`6.20 araç`**
* **Epizot 50 (Final):** Ort. Bekleme = `11.61 sn`, Ort. Kuyruk = `7.07 araç`, TD Loss = `0.0665`

**Aynı Trafik Senaryosu (`seed=42`, `1800 sn` Zirve Testi) Üzerinde 3 Modun Resmi Karşılaştırması (`results/cologne3_corridor_summary.csv`):**

| Kontrol Modu | Ort. Bekleme Süresi | Ort. Kuyruk Uzunluğu | Ort. Seyahat Süresi | Toplam $CO_2$ Salınımı | Ort. Hız |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Fixed-Time (Sabit Süreli Klasik)** | `33.09 sn` | `18.34 araç` | `82.88 sn` | `91.86 kg` | `9.29 m/s` |
| **2. Actuated (Klasik Sıralı Sensörlü)** | `31.00 sn` (*-%6.3*) | `14.02 araç` | `83.17 sn` | `82.80 kg` | `9.78 m/s` |
| **3. DQN RL (4 Fazlı Akıllı Faz Atlama)** | **`14.40 sn`** (**-%56.5**) | **`7.30 araç`** (**-%60.2**) | **`62.77 sn`** (**-%24.3**) | **`54.80 kg`** (**-%40.3**) | **`10.38 m/s`** |

> **Temel Bulgu:** Eğitilmiş DQN modeli, sabit süreli sisteme kıyasla bekleme süresini **%56.5**, klasik sıralı sensörlü (Actuated) sisteme kıyasla ise **%53.5** oranında azaltmıştır.

---

## 4. Depo (Repository) Dosya Yapısı ve Çalıştırma Rehberi

```text
adaptive-traffic-signal-rl/
├── src/
│   ├── rl_agent.py                # DeepPhaseMLP (6->64->64->1), DQNAgent, ReplayBuffer, Checkpoint kayıt/yükleme
│   ├── corridor3_runner.py        # RealNetworkSimulation, 4 fazlı akıllı faz atlama, 3 modlu benchmark ve eğitim döngüsü
│   └── update_charts_and_report.py# Eğitim loglarından SVG grafiklerini üreten yardımcı betik
├── models/
│   ├── dqn_resco_cologne.json     # 50 epizot eğitilmiş en iyi (best) sinir ağı ağırlıkları (production model)
│   └── training_checkpoint.json   # Yarıda bırakıp devam etme (resume) için tam eğitim checkpoint dosyası
├── nets/
│   ├── cologne3/                  # Gerçek Köln 3 kavşaklı koridor (.net.xml, .rou.xml, .sumocfg, gui-settings.xml)
│   └── cologne1/                  # Gerçek Köln tekil kavşak (.net.xml, .rou.xml, .sumocfg)
├── results/
│   ├── training_log.csv           # 50 epizotluk eğitim geçmişi (wait, queue, loss, epsilon)
│   ├── cologne3_corridor_summary.csv # 3 modun resmi karşılaştırma metrikleri
│   ├── learning_curve.svg         # 50 epizotluk öğrenme ve loss yakınsama grafiği
│   └── cologne3_comparison.svg    # 3 modlu performans karşılaştırma sütun grafiği
├── docs/
│   ├── MCBU_Midterm_Report.docx   # MCBÜ resmi vize raporu formatında doldurulmuş İngilizce rapor
│   └── MCBU_Midterm_Report.md     # Vize raporunun Markdown karşılığı
└── 1_Mod_... .bat - 6_Egitimi_... .bat # Tek tıkla SUMO-GUI izleme, tablo alma ve eğitim başlatma kısayolları
```

---

## 5. Arkadaşın Yapay Zeka Aracı İçin Prompt / Görev Bağlamı (Final Aşaması Yol Haritası)

Bu projeyi başka bir AI aracına (ChatGPT, Claude, Cursor vb.) verdiğinizde aşağıdaki bağlamı kullanabilirsiniz:
1. **Mevcut Durum:** Vize aşaması için `src/rl_agent.py` ve `src/corridor3_runner.py` içinde merkezi/paylaşımlı ağırlıklı (Parameter-Sharing) 4 fazlı DQN mimarisi tamamlanmış ve `models/dqn_resco_cologne.json` içine eğitilmiştir.
2. **Final (Haziran) Aşaması İçin Eklenmesi Planlanan 3 Yeni Özellik:**
   * **Modül 1 — Komşu Kavşak Haberleşmesi (Multi-Agent Green Wave):** `cologne3` içindeki 3 kavşağın (`359566`, `360086`, `360082`) birbirine doğru gelen araç gruplarını (upstream/downstream platoon pressure) `extract_phase_features` fonksiyonuna 7. ve 8. öznitelik olarak eklemek.
   * **Modül 2 — Acil Durum Aracı Önceliği (Emergency Vehicle Preemption - EVP):** Şeritlerde ambulans/itfaiye (`vType="emergency"`) algılandığında RL kararını güvenli biçimde (`min_green` ve `yellow_time` kurallarını bozmadan) override ederek koridoru yeşile açmak.
   * **Modül 3 — İnteraktif Görselleştirme / Dashboard:** `results/` altındaki CSV verilerini ve canlı simülasyon metriklerini gösteren bir arayüz (Streamlit veya web paneli) hazırlamak.
