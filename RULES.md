# RULES.md — Kodlama Standartları ve Sistem Koruma Kuralları

Bu doküman, mevcut çalışan **NeurIPS 2021 RESCO Cologne-3** trafik kontrol sistemini, eğitilmiş model ağırlıklarını (`models/dqn_resco_cologne.json`) ve resmi karşılaştırma sonuçlarını bozmamak için projeye katkı sağlayan tüm geliştiricilerin ve araştırmacıların uyması gereken **zorunlu kuralları** tanımlar.

---

## 1. Harita ve Veri Seti Bütünlüğü Kuralları (KRİTİK)

1. **`src/build_networks.py` Betiğini ASLA Çalıştırma:**
   * `nets/cologne3/` ve `nets/cologne1/` dizinlerinde gerçek **Almanya / Köln (RESCO Benchmark)** haritaları (`cologne3.net.xml`, `cologne3.rou.xml`, `begin=25200`, `end=28800`) bulunmaktadır.
   * `src/build_networks.py` dosyası projenin ilk günlerinden kalma sentetik bir ızgara üretecidir. Çalıştırılması halinde gerçek Köln haritalarının üzerine yazar. Bu dosya yalnızca tarihsel referans olarak tutulmaktadır; **kesinlikle çalıştırılmamalıdır**.
2. **`.sumocfg` Zaman Aralığını Koruma:**
   * Gerçek Köln araç rotaları sabah `07:00–08:00` (`25200` ile `28800` saniyeler arası) için tanımlıdır. `cologne3.sumocfg` ve `cologne1.sumocfg` içindeki `<begin value="25200"/>` değeri `0` olarak değiştirilmemelidir (aksi takdirde ilk 7 saat boyunca harita boş çalışır).

---

## 2. Eğitilmiş Model ve Geriye Dönük Uyumluluk Kuralları

1. **Üretim Modelini (`models/dqn_resco_cologne.json`) Ezmeme Kuralı:**
   * `models/dqn_resco_cologne.json`, 50 epizot boyunca eğitilmiş ve sabit süreli sisteme kıyasla bekleme süresini **%56.5**, sensörlü sisteme kıyasla **%53.5** azalttığı doğrulanmış vize teslim modelidir.
   * Yeni bir ödül fonksiyonu, hiperparametre veya çoklu-ajan (Multi-Agent) denemesi yapılırken çıktı modeli **farklı bir dosya adıyla** (ör. `models/dqn_cologne3_marl.json`) kaydedilmeli; yalnızca mevcut `14.40 sn` ortalama bekleme derecesinden daha iyi olduğu kanıtlandığında ana model güncellenmelidir.
2. **Ağ Giriş Boyutu (`in_dim = 6`) Uyumluluğu:**
   * `src/rl_agent.py` içindeki `DeepPhaseMLP` sınıfı `6 -> 64 -> 64 -> 1` mimarisine sahiptir ve `models/dqn_resco_cologne.json` içindeki `w1` matrisi `64 x 6` boyutundadır.
   * Final aşamasında durum vektörüne yeni öznitelikler (ör. komşu kavşak kuyruk bilgisi veya acil durum aracı bayrağı) eklendiğinde:
     * Mevcut 6 boyutlu vize modelinin (`1..4` numaralı `.bat` dosyalarının) sorunsuz çalışmaya devam etmesi için `in_dim` dinamik tutulmalı veya yeni özellikler opsiyonel bir bayrak (`enable_comm: bool = False`) ile devreye alınmalıdır.

---

## 3. Trafik Mühendisliği ve Güvenlik Kısıtları (Safety Invariants)

Hiçbir kontrol modu (`fixed`, `actuated`, `dqn` veya eklenecek `evp` / `marl` modları) aşağıdaki fiziksel güvenlik kurallarını ihlal edemez:

1. **Zorunlu Sarı Işık Geçişi (`yellow_time = 3` sn):**
   * Bir yeşil fazdan (`Faz 0, 2, 4, 6`) başka bir yeşil faza geçilirken doğrudan yeşil faz indeksi atanamaz.
   * Önce mevcut yeşil fazın bir sonraki indeksi olan sarı faz (`yellow_sumo_phase = cur_sumo_phase + 1`) `traci.trafficlight.setPhase()` ile atanmalı ve `pending_yellow[tl] = 3` saniye boyunca geri sayım tamamlandıktan sonra hedef yeşil faza geçilmelidir.
2. **Minimum ve Maksimum Yeşil Süre Kısıtları:**
   * **Minimum Yeşil:** Ana fazlar (`is_turn == False`) için `min_green_major = 10` sn, korumalı sola dönüş fazları (`is_turn == True`) için `min_green_turn = 4` sn dolmadan faz değiştirilemez (ışık titremesi / flickering önlenir).
   * **Maksimum Yeşil (Starvation Önleme):** Ana fazlar için `max_green_major = 45` sn, dönüş fazları için `max_green_turn = 10` sn aşıldığında bekleyen diğer yönlere geçiş zorlanmalıdır.
3. **Karar Periyodu (`delta_time = 5` sn):**
   * `traci.simulationStep()` her `1` saniyede bir ilerlerken, ajan kararları `sim_t % self.delta_time == 0` adımlarında (ve yalnızca `pending_yellow[tl] == 0` iken) alınmalıdır.

---

## 4. Adil Kıyaslama (Fair Benchmark) Kuralları

1. **Birebir Aynı Senaryo ve Tohum (`seed = 42`):**
   * `run_benchmark_comparison()` fonksiyonunda karşılaştırılan tüm kontrolcüler birebir aynı `sumocfg_path`, aynı `sim_duration` (`1800` sn) ve aynı `seed=42` ile çalıştırılmalıdır.
2. **Gerçek SUMO Metrikleri:**
   * Ortalama bekleme süresi (`waitingTime`), zaman kaybı (`timeLoss`) ve seyahat süresi (`duration`) doğrudan SUMO'nun ürettiği `--tripinfo-output` XML dosyasından; kuyruk uzunluğu (`getLastStepHaltingNumber`) ve emisyon (`getCO2Emission`) doğrudan `traci.lane` API'sinden hesaplanmalıdır.

---

## 5. Kodlama, Dosya Sistemi ve Konsol Standartları (Windows & Python 3.14)

1. **Python Yorumlayıcı Yolu:**
   * Geliştirme ortamında Windows Store `WindowsApps\python.exe` takma adı (alias) çakışmasını önlemek için `.bat` dosyalarında ve otomasyon komutlarında doğrudan `C:\Users\besir_secilmis\AppData\Local\Python\bin\python.exe` (veya ortamda doğrulanmış Python yolu) kullanılmalıdır.
2. **Konsol Çıktılarında Emoji Yasağı (`cp1254` / `cp857` Uyumluluğu):**
   * Windows terminalinde `UnicodeEncodeError: 'charmap' codec can't encode character` hatasına yol açmamak için Python `print()` ve `sys.stdout.write()` ifadelerinde **emoji (`✅`, `🚀`, `⚠️` vb.) veya ASCII dışı özel semboller kullanılmamalıdır**.
   * Bunun yerine `[OK]`, `[BILGI]`, `[DURDURULDU]`, `[TAMAMLANDI]`, `[YENI REKOR!]` gibi saf ASCII etiketler kullanılmalıdır.
3. **Dosya Kodlaması (`encoding="utf-8"`) ve Yol Yönetimi (`pathlib.Path`):**
   * Tüm JSON, CSV, XML, SVG ve Markdown okuma/yazma işlemlerinde `encoding="utf-8"` parametresi zorunludur.
   * Dosya yolları çalışma dizininden bağımsız olması için `BASE_DIR = Path(__file__).resolve().parent.parent` referans alınarak `pathlib.Path` ile oluşturulmalıdır.
4. **Güvenli `TraCI` Bağlantı Yönetimi:**
   * Yeni bir simülasyon başlatmadan önce açık kalmış olabilecek `traci` oturumlarını kapatmak için daima:
     ```python
     try:
         traci.close()
     except Exception:
         pass
     ```
     kalıbı kullanılmalı ve eğitim döngüleri `KeyboardInterrupt` yakaladığında `traci.close()` çağrısı yaptıktan sonra son tamamlanan checkpoint'i koruyarak çıkmalıdır.
5. **Eski Prototip Dosyalarıyla Karıştırmama:**
   * `src/env.py`, `src/baselines.py`, `src/evaluate.py` ve `src/demo_gui.py` eski 2 fazlı sentetik prototipe aittir. Yeni özellikler bu eski dosyalara değil, doğrudan **`src/corridor3_runner.py`** ve **`src/rl_agent.py`** (veya yeni oluşturulacak modüllere) entegre edilmelidir.
