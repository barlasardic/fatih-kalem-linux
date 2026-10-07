# Fatih Kalem Linux

**Ekranın üstüne yazın.** Pardus ETAP etkileşimli tahtaları için şeffaf katman
çizim uygulaması.

[English below](#english) · [Pardus ETAP](#pardus-etap) · [Kurulum](#kurulum) ·
[M1 kapsam](#m1-kapsamı) · [Yol haritası](#yol-haritası)

---

## Bu ne?

Fatih Kalem, öğretmenin ekranı kapattırmadan ders kitabının, bir PDF'in, bir
videonun ya da herhangi bir uygulamanın **üzerine kalemle yazmasını** sağlayan
bir uygulamadır: program tüm ekranın üstüne saydam bir katman açar.

Bu depo, öğretmenlerin Windows'ta kullandığı *Fatih Kalem*'in Linux için sıfırdan
yazılmış, özgün bir uygulamadır. Pardus ETAP'ta bulunan mevcut **Pardus Kalem**
(`pardus/pardus-pen`) beyaz tahta/PDF odaklıdır; bu uygulamanın farkı
**şeffaf katman annotasyonudur** — açık uygulamayı kapatmadan üstüne yazma.

> **MEB ile ilgisi yoktur.** Bu, MEB'ye bağlı olmayan, bağımsız ve açık kaynak
> bir projedir. Fatih Kalem, TÜBİTAK BİLGEM / MEB projesidir ve bu depo o
> yazılımın kaynak kodu değildir; yalnızca fikri ve iş akışı referans alınmıştır.

### Öne çıkanlar

| | |
|---|---|
| **Katman** | Her uygulamanın üstünde saydam tuval; tek tuşla alttaki uygulamaya geçiş |
| **Kalem** | 24 renk × 6 kalınlık × 3 uç tipi (düz / kesik / Arapça kırık uç) |
| **Foslu kalem** | Saydam geçişli vurgulayıcı; eklem noktalarında birikmez |
| **Silgi** | 4 farklı boy, kısmi (piksel) silme; geri alınabilir |
| **Gerçek kalem** | Basınç, avuç içi reddetme, kalemin arka ucuyla silme (M4) |
| **Geçmiş** | 4K tahtada bellek taşımayan, yalnızca kirli dikdörtgeni saklayan geri al/yinele |
| **Ekran görüntüsü** | Çizimin kendisi (şeffaf PNG) veya ekran + çizim (PNG/JPEG/PDF) |
| **Çok dilli** | Türkçe ve İngilizce, tek dosyada katalog |
| **Hafif** | Qt dışında hiçbir bağımlılık yok; 2 GB RAM'li bir tahtada çalışır |

## Hedef ortam

- **Pardus ETAP 23+ / Cinnamon** (X11) — birincil hedef
- Ubuntu / Debian / Xfce / MATE gibi **X11** oturumları
- KDE Plasma **Wayland** — kısmen (aşağıya bakın)

```
$ ./tools/run.sh --print-session
platform : linux
Qt       : xcb
DISPLAY  : :0
desktop  : X-Cinnamon
backend: x11
global overlay      : yes
click-through regions: yes
screen capture      : yes
global hotkeys      : yes
always on top        : yes
```

> ### Wayland notu
> Wayland, bir uygulamanın diğer bütün pencerelerin üstüne saydam katman
> açmasına izin vermez — yığınlama kararı compositor'da (KWin) verilir. Bu bir
> uygulama hatası değil, protokolün kısıtıdır. Uygulama Wayland'da bir pencere
> moduna düşer ve bunu açıkça söyler. Pardus ETAP X11 kullandığı için tahta
> tarafında bu sorun yoktur.

## Kurulum

### Pardus / Ubuntu — kaynaktan

```bash
sudo apt update
sudo apt install python3-pyqt6        # çalıştırmak için tek bağımlılık
./packaging/install.sh                # ya da kurulum yapmadan:
./tools/run.sh
```

`install.sh` kullanıcı dizinine (`~/.local`) kurar, `.desktop` kaydı ekler ve
oturum açılışında kendiliğinden başlamasını sağlar. `--uninstall` ile geri
alınır, `sudo` gerekmez.

### AppImage

AppImage paketlemesi M5 sürümünde yayınlanacak. Şimdilik
[Releases](https://github.com/BarlasArdic/fatih-kalem-linux/releases) sayfasını
kontrol edin.

## Komut satırı

```
fatih-kalem                  # tam ekran şeffaf katman
fatih-kalem --sandbox        # normal pencere (arayüz geliştirme)
fatih-kalem --print-session  # oturum yeteneklerini yazdır
fatih-kalem --reset-config   # varsayılan ayarlar
fatih-kalem --tool eraser --width 48 --color '#1f6feb'
fatih-kalem --board white    # ekranın yerine beyaz zemin
```

### Ayarlar

Tüm ayarlar düz bir INI dosyasında: `~/.config/fatih-kalem-linux/fatih-kalem-linux.ini`.
Bir tahtaya uzaktan `ssh` ile bağlanıp önceden ayar yazmak mümkündür.

### Kısayollar

| Tuş | İşlev |
|---|---|
| `Ctrl+Z` / `Ctrl+Shift+Z` | Geri al / yinele |
| `Ctrl+PgDown` | Ekranı temizle |
| `Ctrl+Alt+P` | Alttaki uygulamaya geç |
| `Ctrl+Shift+S` | Ekran görüntüsü |
| `Esc` | Kalemi gizle |

> Not: X11'de katman `override-redirect` penceresidir ve hiçbir zaman klavye
> odağını almaz — bu yüzden gerçek global kısayollar M4'te `XGrabKey` ile kök
> pencereye bağlanacaktır. Tablo, pencere odağı alınabildiği oturumlar içindir.

## M1 kapsamı

Bu depodaki ilk sürüm (v0.1.0) çalışan bir çekirdektir:

- ✅ şeffaf tam ekran katman + araç çubuğu (sürüklenir, kenara yapışır)
- ✅ tık geçirgenliği (katmanı alttaki uygulamaya bırak)
- ✅ kalem / foslu kalem / silgi, 3 uç tipi, renk ve kalınlık döngüleri
- ✅ geri al / yinele / temizle
- ✅ basınç duyarlı kalem (basınç yoksa sabit genişliğe düşer)
- ✅ ekran görüntüsü → PNG / JPEG / PDF
- ✅ Türkçe / İngilizce
- ⏳ renk paleti ızgarası, ayarlar penceresi, şekiller, perde, arka planlar (M2/M3)

Planın tamamı [docs/ROADMAP.md](docs/ROADMAP.md) içinde.

## Geliştirme

```bash
./tools/run.sh --sandbox        # arayüzü normal pencerede çalıştır
./scripts/test.sh               # 106 test (pytest varsa o, yoksa unittest)
QT_QPA_PLATFORM=xcb ./tools/run.sh   # bu makinede gerçek X11 katmanı
```

Kod düzeni:

```
src/fatih_kalem/
├── core/       çizgi motoru, undo yığını, veri modeli   ← test edilebilir çekirdek
├── platform/   X11 / Wayland farkları                   ← tek yerde
├── ui/         katman, araç çubuğu, ikonlar, tema
├── export/     PNG / JPEG / PDF
└── config.py   INI ayarlar
```

`core/` bilerek widget'lardan bağımsız tutuldu; ağır işler (geometri, undo,
serileştirme) ekran sunucusu olmadan test ediliyor.

## Test etiketi

`docs/TESTING-ETAP.md` — gerçek tahta üzerinde elle test listesi. Bir tahtanız
varsa katkınızı açmadan önce bu listeyi gezin.

## Katkı

Türkçe veya İngilizce, [CONTRIBUTING.md](CONTRIBUTING.md) kurallarına göre.
Katkı göndermeden önce `./scripts/test.sh` çalışıyor olmalı.

## Lisans

GPL-3.0-or-later — [LICENSE](LICENSE). Pardus ekosistemindeki diğer eğitim
uygulamalarıyla aynı lisans.

---

# English

**Write over the whole screen.** A transparent annotation layer for Pardus ETAP
interactive whiteboards.

Fatih Kalem opens a transparent layer above *everything* on the board, so a
teacher can write on a textbook PDF, a video, a web page or any running
application without closing it.

This repository is an independent, clean-room Linux application inspired by the
workflow of *Fatih Kalem* on Windows. It is **not** affiliated with TÜBİTAK
BİLGEM or MEB, and contains none of its code. The existing **Pardus Kalem**
(`pardus/pardus-pen`) is a whiteboard/PDF app; this project is about the
*overlay*.

### Highlights

- Transparent click-through overlay, with one-button hand-back to the app below
- 24 inks × 6 widths × 3 nib types (solid / dashed / Arabic broken nib)
- Translucent highlighter, 4-size partial eraser, undo/redo
- Dirty-rectangle undo: no 33 MB snapshot per step on a 4K board
- Export ink only (transparent PNG) or screen + ink (PNG/JPEG/PDF)
- Turkish and English
- One dependency: PyQt6

### Requirements

- Linux with **X11** (Pardus ETAP 23+ / Cinnamon is the primary target)
- `python3-pyqt6`
- On Wayland the overlay degrades to a normal window; this is a protocol limit,
  not a bug

### Run

```bash
sudo apt install python3-pyqt6
./packaging/install.sh        # or: ./tools/run.sh
./tools/run.sh --sandbox      # develop the UI in a normal window
./tools/run.sh --print-session
```

### Development

```bash
./scripts/test.sh                          # 106 tests, stdlib unittest
QT_QPA_PLATFORM=xcb ./tools/run.sh         # exercise the real X11 overlay
```

`src/fatih_kalem/core/` holds the geometry, undo and serialisation logic and is
deliberately free of widgets so it can be tested without a display server.

### License

GPL-3.0-or-later. See [LICENSE](LICENSE).