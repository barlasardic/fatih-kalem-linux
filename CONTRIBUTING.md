# Katkı / Contributing

Türkçe veya İngilizce katkılar memnuniyetle karşılanır.

## Başlamadan önce

```bash
sudo apt install python3-pyqt6        # tek bağımlılık
./tools/run.sh --sandbox              # arayüzü normal pencerede aç
./scripts/test.sh                     # testler yeşil olmalı
```

## Kurallar

1. **Test ekleyin.** `core/` içindeki her davranış değişikliği için test. Testler
   `unittest` ile yazılır; `pytest` varsa o kullanılır.
2. **`core/` widget'lardan bağımsız kalsın.** `core/` altında `PyQt6.QtWidgets`
   import'u olmamalı — oradaki mantık ekran sunucusu olmadan test edilir.
3. **Yorum yazmayın, ne yaptığını anlatın.** Kod kendini anlatır; yorum sadece
   *neden* için.
4. **Satır uzunluğu 100 karakter.**
5. **Yeni ayar ekliyorsanız** `config.py` içindeki `DEFAULTS` sözlüğüne de
   ekleyin; ayarlar kendini belgeleyen bir INI olarak yazılır.
6. **Yeni metin ekliyorsanız** İngilizce yazıp `i18n.py` kataloğuna ekleyin,
   sonra `./scripts/update-translations.sh` çalıştırın.

## Commit stili

```
kısa özet (imperatif, 72 karakter altı)

Gerekçe ve değişikliğin etkisi. Gerekirse "neden" sorusuna cevap verin.
```

Örnekler:

```
Kesik çizgilerde boşluğu kalem genişliğine göre genişlet

Yuvarlak uçlar genişlik/2 kadar açılıyor; 12 px kalemde 10 px'lik boşluk
kapanıyor ve çizgi düz görünüyordu.
```

## Mimari notlar

`docs/ROADMAP.md` dosyasındaki karar tablosunu okuyun. Özellikle şu üç şey:

- Katman `override-redirect` penceredir, klavye odağı alamaz. Odak gereken
  kısayollar `XGrabKey` ile kök pencereye bağlanmalı (M4).
- Undo, tam ekran kopya değil kirli dikdörtgen yamasıdır. Bellek tavanı
  `core/undo.py` içinde; aşan adımlar en eskiden düşer.
- Yarı saydam çizgiler scratch layer'da çizilir. Doğrudan `QPainter` ile
  çizerseniz eklem noktalarında alfa birikir.

## Commit öncesi kontrol

```bash
./scripts/test.sh
python3 -m compileall -q src
```

## Rapor

Hata: [Issues](https://github.com/BarlasArdic/fatih-kalem-linux/issues)
Bir hata raporunda mutlaka olsun:

- Pardus sürümü (`cat /etc/os-release`) ve Cinnamon sürümü
- `--print-session` çıktısı
- Tahta çözünürlüğü ve dokunmatik/pen donanımı (`libinput list-devices`)
- Hatanın ekran görüntüsü
