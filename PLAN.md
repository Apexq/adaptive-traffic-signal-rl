# PLAN.md — Proje İlerleme Durumu ve Sonraki Adımlar Yol Haritası

Bu doküman, **`adaptive-traffic-signal-rl`** bitirme projesinde şu ana kadar tamamlanan çalışmaları ve mevcut kod tabanını (`src/corridor3_runner.py`, `src/rl_agent.py`) bozmadan **Final (Haziran)** teslimine kadar izlenecek somut mühendislik adımlarını tanımlar.

---

## 1. Tamamlanan Aşamalar (Vize / Midterm Hedefleri — %100 Tamamlandı)

- [x] **Gerçek Dünya Haritası Entegrasyonu (NeurIPS 2021 RESCO Benchmark):**
  - Almanya / Köln-Lindenthal **Dürener Straße** üzerindeki 3 ardışık sinyalize kavşağı içeren `nets/cologne3/` (`359566`, `360086`, `360082`) ve tekil kavşak `nets/cologne1/` (`357187`) gerçek sabah zirve saati (`25200–28800 sn`) verileriyle projeye dahil edildi.
- [x] **Dinamik Topoloji Keşfi ve Trafik Güvenlik Durum Makinesi (`src/corridor3_runner.py`):**
  - `RealNetworkSimulation` sınıfı ile XML ağından 4 yeşil fazın (`Faz 0, 2, 4, 6`) ve şerit bağlantılarının otomatik keşfi sağlandı.
  - Zorunlu sarı ışık (`yellow_time = 3s`), minimum yeşil (`10s` ana faz / `4s` dönüş fazı) ve maksimum yeşil (`45s` ana faz / `10s` dönüş fazı) kısıtları kodlandı.
- [x] **4 Fazlı Akıllı Faz Atlama ve Derin Q-Ağı (`src/rl_agent.py`):**
  - Boş sola dönüş fazlarını (`Faz 2` ve `Faz 6`, `halt_cnt < 2` ve `wait_sum < 25s`) atlayan `valid_mask` mekanizması geliştirildi.
  - `%100` rastgele *He Normal* ağırlıklarla başlatılan `DeepPhaseMLP` (`6 -> 64 -> 64 -> 1`) sinir ağı, Replay Buffer (`20,000`), Target Network ve epizot bazlı Checkpoint/Resume (`models/training_checkpoint.json`) sistemi tamamlandı.
- [x] **50 Epizotluk Gerçek Eğitim ve 3 Modlu Benchmark Doğrulaması:**
  - `cologne3` koridorunda 50 tam saatlik (`50 x 3600 sn`) eğitim tamamlandı; en iyi model ağırlıkları `models/dqn_resco_cologne.json` dosyasına kaydedildi (Epizot 44 bekleme rekoru: **`8.67 sn`**).
  - `1800 sn` zirve testi (`seed=42`) karşılaştırmasında:
    - `1. Fixed-Time (Sabit Süreli)`: `33.09 sn` bekleme | `18.34` araç kuyruk | `91.86 kg` $\text{CO}_2$
    - `2. Actuated (Klasik Sıralı Sensörlü)`: `31.00 sn` bekleme (`-%6.3`) | `14.02` araç kuyruk | `82.80 kg` $\text{CO}_2$
    - `3. DQN RL (4 Fazlı Akıllı Faz Atlama)`: **`14.40 sn` bekleme (`-%56.5`)** | **`7.30` araç kuyruk (`-%60.2`)** | **`54.80 kg` $\text{CO}_2$ (`-%40.3`)**
- [x] **Tek Tıkla Çalıştırma Betikleri ve Vize Raporu Dokümantasyonu:**
  - Kök dizindeki `1..6` numaralı `.bat` başlatıcıları, `results/*.svg` grafikleri, `docs/MCBU_Midterm_Report.docx` resmi vize raporu ve `docs/Executive_Summary.pdf` yönetici özeti oluşturuldu.

---

## 2. Sıradaki Adımlar (Vize Sunumu ve Final Dönemi Geliştirme Planı)

### Adım 1: Vize Rapor Teslimi ve Canlı Sunum (Kasım 2026)
- [ ] **1.1. Danışman Hoca Kontrolü ve Rapor Teslimi (23 Kasım):**
  - `docs/MCBU_Midterm_Report.docx` dosyasının teslim edilmesi.
- [ ] **1.2. Vize Sunumu Canlı Gösterimi (24 Kasım):**
  - Sunum sırasında `4_Tum_Modlari_Hizli_Karsilastir_Tablo.bat` ile canlı terminal tablosunun gösterilmesi.
  - `1_Mod_Sabit_Sureli_3Kavsak_Izle.bat` ve `3_Mod_Akilli_RL_DQN_3Kavsak_Izle.bat` ile SUMO-GUI üzerinde Köln Dürener Straße koridorunda kuyruk farkının canlı izletilmesi.

---

### Adım 2: Multi-Agent Komşu Kavşak Haberleşmesi ve Yeşil Dalga (Final — Modül 1)
> **Hedef:** Şu an `cologne3` içindeki 3 kavşak (`359566`, `360086`, `360082`) aynı eğitilmiş ağırlıkları paylaşmakta ancak birbirlerinin kuyruk/faz durumunu bilmemektedir. Bu adımda kavşaklar arası bilgi paylaşımı (Multi-Agent Communication) eklenecektir.

- [ ] **2.1. Komşu Kavşak Topoloji Eşleştirmesi (`src/corridor3_runner.py`):**
  - `_discover_network_topology()` içinde her kavşağın çıkış şeritlerinin (`outgoing lanes`) hangi komşu kavşağın giriş şeritlerine (`incoming lanes`) bağlandığını otomatik bulan `_discover_neighbor_links()` metodunun yazılması.
- [ ] **2.2. Genişletilmiş Faz Öznitelik Vektörü (`in_dim = 8`, Geriye Dönük Uyumlu):**
  - `RealNetworkSimulation.__init__()` içine `use_neighbor_comm: bool = False` parametresinin eklenmesi (`RULES.md` gereği mevcut `in_dim=6` modeli ve `.bat` dosyaları bozulmadan korunur).
  - `use_neighbor_comm=True` olduğunda `_extract_phase_features_and_mask()` fonksiyonuna 2 yeni öznitelik eklenmesi:
    - `f_6 (upstream_platoon_norm)`: Komşu kavşaktan bu kavşağın ilgili fazına doğru yaklaşmakta olan araç sayısı.
    - `f_7 (downstream_spillback_norm)`: Bu fazın gönderdiği komşu kavşak şeridindeki doluluk oranı (ileri kavşak tıkalıysa boşuna yeşil yakmamak / *spillback* önlemek için).
- [ ] **2.3. İşbirlikçi Ödül (Cooperative Corridor Reward) ve Eğitim:**
  - Yerel kavşak ödülüne komşu kavşakların ortalama kuyruk cezasının ($\alpha = 0.25$ ağırlıkla) eklenmesi: $R_i^{\text{coop}} = R_i^{\text{local}} + \alpha \sum_{j \in \mathcal{N}_i} R_j^{\text{local}}$.
  - Eğitilen yeni modelin `models/dqn_cologne3_marl.json` olarak kaydedilmesi ve tekil ajan (`dqn_resco_cologne.json`) ile karşılaştırılması.

---

### Adım 3: Acil Durum Aracı Önceliği — Emergency Vehicle Preemption / EVP (Final — Modül 2)
> **Hedef:** Koridora giren ambulans veya itfaiye araçlarının (`vType="emergency"`) kavşaklarda kırmızı ışıkta beklemeden güvenli yeşil dalga ile geçmesini sağlamak.

- [ ] **3.1. Acil Durum Trafik Senaryosu (`nets/cologne3/cologne3_evp.rou.xml`):**
  - Orijinal `cologne3.rou.xml` dosyasını bozmadan (`RULES.md` Madde 1), zirve saatinde koridor boyunca ilerleyen `vType="emergency"` (ambulans/itfaiye) araçlarını içeren ek rota yapılandırmasının hazırlanması.
- [ ] **3.2. Güvenli Preemption (Öncelik) Mantığı (`src/corridor3_runner.py`):**
  - Her karar adımında (`sim_t % delta_time == 0`) kavşağa yaklaşan şeritlerde `traci.lane.getLastStepVehicleIDs(lane)` üzerinden acil durum aracı taraması yapılması.
  - Acil durum aracı tespit edilen şeridi kontrol eden yeşil fazın, **`min_green` ve `yellow_time = 3s` güvenlik kurallarını kesinlikle çiğnemeden** öncelikli hedef faz (`desired_idx`) olarak seçilmesi.
- [ ] **3.3. Acil Durum Metriklerinin Ölçümü:**
  - `run()` çıktısına `ev_avg_waiting_time_s` (ambulans ortalama bekleme süresi) ve `ev_avg_travel_time_s` (ambulans koridor geçiş süresi) metriklerinin eklenmesi.

---

### Adım 4: İnteraktif Karşılaştırma Dashboard'u ve Final Tez Raporu (Final — Modül 3)
- [ ] **4.1. 4 Modlu Kapsamlı Benchmark (`Fixed-Time` vs `Actuated` vs `DQN` vs `MARL+EVP`):**
  - Tüm kontrol modlarının hem standart trafik hem de acil durum senaryosunda çoklu tohum (`seeds = [42, 101, 202, 303, 404]`) ile koşturulup `results/final_corridor_benchmark.csv` tablosunun üretilmesi.
- [ ] **4.2. Görsel Analiz ve Karşılaştırma Arayüzü (`src/dashboard.py`):**
  - `results/` altındaki eğitim eğrilerini, kavşak bazlı kuyruk değişimlerini, $\text{CO}_2$ tasarrufunu ve ambulans geçiş sürelerini grafiksel olarak sunan bir gösterge paneli hazırlanması.
- [ ] **4.3. MCBÜ Bitirme Projesi Final Tez Raporu:**
  - Elde edilen tüm tabloların, mimari diyagramların ve deneysel analizlerin final tez şablonuna (`docs/MCBU_Final_Report.docx`) aktarılması.
