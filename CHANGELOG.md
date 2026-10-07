# Değişimler

## [v0.1.0] — 2026-10-07

İlk çalışan çekirdek (M1).

### Eklenen
- Şeffaf tam ekran katman (`override-redirect`) + araç çubuğu
- Tık geçirgenliği: çizim modunda tam ekran, geçiş modunda yalnızca araç çubuğu
- Kalem, foslu kalem, silgi; 24 renk paleti, 6 kalınlık, 3 uç tipi
  (düz / kesik / Arapça kırık uç)
- Basınç duyarlı genişlik; basınç bildirmeyen cihazda sabit genişliğe düşer
- Kirli dikdörtgen tabanlı geri al / yinele, bellek tavanı, PNG sıkıştırmalı
  büyük yamalar
- Ekran görüntüsü: çizim only (şeffaf PNG) veya ekran + çizim (PNG/JPEG/PDF)
- Türkçe ve İngilizce arayüz
- X11 EWMH yığınlama (`ABOVE`, `STICKY`) ve Wayland kısıtı için uyarı
- `--sandbox` geliştirme kipi, `--print-session` teşhis aracı
- 110 test

### Düzeltilen
- AppImage build betiğinde yorum satırı, backslash ile devam eden komutun
  içinde kaldığı için `--exclude-module` bayrakları uygulanmıyordu
- PyInstaller giriş noktası bağıl import kullandığı için PyQt6 hiç
  paketlenmiyordu; `packaging/entrypoint.py` eklendi
- `packaging/install.sh` başka bir dizinden çalıştırıldığında bozuk bir
  launcher yazıyordu; yollar artık betiğin konumundan çözülüyor

### Bilinen sınırlar (M2-M4)
- Renk paleti ızgarası, ayarlar penceresi, perde, şekiller, arka planlar yok
- Avuç içi reddetme ve iki parmak jestleri uygulanmadı
- X11'de pencere klavye odağı alamıyor; global kısayollar kök pencereye
  bağlanacak (M4)
