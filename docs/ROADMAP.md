# Yol Haritası

Fatih Kalem Linux geliştirme planı. Hedef ortam: **Pardus ETAP 23+ / Cinnamon
(X11)**, 4K dokunmatik akıllı tahta.

## Mimari kararlar (baştan sabit)

| Karar | Gerekçe |
|---|---|
| Katman `override-redirect` pencere | Muffin'in pencereyi kapatmasını/indirmesini imkânsız kılar |
| Tık geçirgenliği `QWidget.setMask(QRegion)` | Qt bunu X11'de XShape input region'a çevirir; ek kütüphane yok |
| Araç çubuğu katmanın **çocuk** penceresi | Z-sıralaması önemsiz; geçirgen bölge tek dikdörtgen |
| Undo, tam ekran kopya değil **kirli dikdörtgen yaması** | 4K'da adım başına 33 MB yerine birkaç KB |
| Canlı çizim layer'a yazılmaz | Her pointer olayında layer kopyalanmaz |
| Yarı saydam çizgiler scratch layer'da | Eklem noktalarında alfa birikmez |
| `core/` widget'lardan bağımsız | Ağır mantık ekran sunucusu olmadan test edilir |
| Prosedürel arka planlar (ikili dosya yok) | Depo küçük, 4K'da keskin |
| İkonlar QPainter ile çizilir (SVG yok) | QtSvg yok; yeniden ölçekleme bedava |
| Çeviri tek dosyada katalog | `lrelease` gerektirmez, çift dil ilk günden çalışır |

---

## M1 — Çalışan çekirdek (`v0.1.0`) ✅

Riski en yüksek parçayı önce kanıtlamak için: şeffaf katman + geçirgenlik.

- [x] Repo iskeleti, GPL-3.0, `pyproject.toml`, pytest/unittest altyapısı
- [x] `Config`: INI ayarlar, tip güvenli erişim, `seed_missing`
- [x] `core/models.py`: `Stroke`, `PenStyle`, `Document`, undo payload'ları
- [x] `core/stroke_engine.py`: örnekleme, yumuşatma, basınç→genişlik, kesik çizgi
- [x] `core/undo.py`: kirli dikdörtgen yama yığını, bellek tavanı, PNG sıkıştırma
- [x] `platform/x11.py`: EWMH `ABOVE` / `STICKY` / `XRaiseWindow`
- [x] `platform/wayland.py`: kısıtlı kip + kullanıcıya açık uyarı
- [x] `ui/canvas.py`: ink katmanı, mouse/touch/stylus yönlendirme
- [x] `ui/toolbar.py`: sürüklenebilir, kenara yapışan, yüksekliğe sığan dikey şerit
- [x] `ui/icons.py`, `ui/theme.py`: QPainter ikonları, 24 renk paleti
- [x] `ui/overlay.py`: katman, geçirgenlik, yakalama, kısayollar, `--sandbox`
- [x] `export/png.py`: PNG / JPEG / PDF, üzerine yazmama garantisi
- [x] `i18n.py`: TR + EN
- [x] 106 test
- [x] README, kurulum betiği, .desktop, TESTING-ETAP.md

### M1'de öğrenilenler

1. **Yuvarlak uçlar kesik çizgi boşluklarını yutuyordu.** Kalem genişliği/2
   kadar her uç açılıyor; 12 px'lik bir kalemde 10 px'lik boşluk kapanıyordu.
   Çözüm: boşluk uzunluğu `genişlik × 1.15`'in altına düşürülemez.
2. **Undo yaması `SourceOver` ile yapıştırılırsa silmez.** Saydam "önceki"
   pikseller yeni mürekkebin üstüne karışır, geri alma hiçbir şey yapmıyormuş
   gibi görünür. Yamalar `CompositionMode_Source` ile değiştirmeli.
3. **Kesik çizgi kalem-düzeyinde `QPen` deseniyle çalışmıyor.** Her `drawLine`
   deseni baştan başlatıyor. Desen, merkez hat boyunca yay uzunluğu ölçülerek
   üretilmeli.

---

## M2 — Kullanılabilir sürüm

- [ ] **Renk paleti paneli**: 24 renk 6×4 ızgara + favoriler, 72 px dokunmatik
      hedef; `PC` renk örneği
- [ ] **Kalınlık paneli**: 6 kalınlık, gerçek fırça önizlemesiyle
- [ ] **Silgi paneli**: 4 boy + kısmi/tam ayrımı
- [ ] **Uç tipi seçimi**: düz / kesik / kırık (Arapça)
- [ ] **Ayarlar penceresi**: dil, kalem, katman, jest, yakalama sekmeleri
- [ ] Araç çubuğu düzenlenebilirliği: sürükle-bırak, gizle/göster, sıralama
- [ ] Uzun basış → "hızlı erişim" satırı
- [ ] Sistem tepsisi ikonu ve menüsü
- [ ] Köşe çağırma okları (öğretmeni bulunduğu köşeye araç çubuğunu getir)

## M3 — Tam özellik

- [ ] **Perde**: bölge kapatma, spotışığı, kayarak açılan perde (tutamacaklı),
      tam ekran, %50 karartma
- [ ] **Geometrik şekiller**: çizgi, ok, dikdörtgen, daire, elips, üçgen, açı
- [ ] **Prosedürel arka planlar**: çizgili, kareli, noktalı, müzik portesi,
      element tablosu, karbon kağıt, beyaz yüzen tahta
- [ ] **Çok sayfalı proje**: `.fkl` kaydet/aç (JSON + zlib)
- [ ] **Görsel kütüphanesi**: dosya seçici + sürükle-bırak, ölçekleme, taşıma
- [ ] Yerleşik (built-in) şekil/görsel kütüphanesi

## M4 — Donanım olgunluğu

- [ ] **Basınç**: uçtan uca doğrulama, ölçüm tablosu (`docs/TESTING-ETAP.md`)
- [ ] **Avuç içi reddetme**: kalem yakınlık durumu + histerezisli öncelik
- [ ] **Kalemin arka ucuyla silme**
- [ ] **Eğim** (tilt) → uç açısı
- [ ] **İki parmak jestleri**: yatay sürükleme = renk döngüsü, dikey = kalınlık,
      iki parmak dokunuş = silgi, kısa çekme = araç çubuğunu çağır
- [ ] **Global kısayollar**: `XGrabKey` ile kök pencereye bağlama (odak gerekmez)
- [ ] Oturum açılışında başlatma (`.config/autostart`)

## M5 — Yayın

- [ ] AppImage (PyInstaller *onedir* + appimagetool, ~90 MB)
- [ ] `nfpm` ile `.deb`
- [ ] GitHub Actions: PR'da test + ruff, tag'de AppImage + Release
- [ ] Çeviriler tamamlanmış `.ts`, `pylupdate`/`lrelease` entegrasyonu
- [ ] Issue/PR şablonları, ekran görüntüleri, tanıtım videosu
- [ ] Pardus Yazılım Merkezi paketi için hazırlık

---

## Bilinen sınırlar

| Sınır | Durum |
|---|---|
| Wayland'da global katman | Mümkün değil (protokol). Uygulama bunu söyler, pencere moduna düşer |
| GNOME Wayland | `layer-shell` yok; XDG portal yalnızca pencere modu sunar |
| 2 GB RAM'li tahta | Katman önbelleği + 192 MB undo tavanı ile sığar; `overlay/hint` kapatılabilir |
| Klavye odağı (X11 override-redirect) | Pencere odağını alamaz; M4'te `XGrabKey` ile çözülür |
| Çoklu ekran | Birincil ekran hedeflenir; `overlay/screen` ile seçilir, birleşik tuval M3'te |

## Dış bağımlılıklar

Zorunlu: **PyQt6** (>= 6.5). İsteğe bağlı: hiçbir şey — ekran görüntüsü Qt'nin
kendi `grabWindow`'ını kullanır, ikonlar çalışma anında çizilir.