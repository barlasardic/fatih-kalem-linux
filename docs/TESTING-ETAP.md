# eTAP Tahtasında Test Listesi

Bu liste, geliştirme makinesinde yapılamayan kontroller için. Her sürüm
yayınlanmadan önce geçilmesi gerekir.

## Ortam

```
$ ./tools/run.sh --print-session
```

| Beklenen | |
|---|---|
| `backend: x11` | Değilse tahta X11 oturumunda değil |
| `desktop  : X-Cinnamon` | Pardus ETAP |
| `global overlay : yes` | |
| `screen capture : yes` | |

Panelde Cinnamon kullanılmıyorsa veya Wayland açıksa uygulama pencere moduna
düşer ve bir uyarı gösterir — bu bir hata değil.

## 1. Katman

- [ ] Uygulamayı başlat → tüm ekranı kaplar, arka uygulama görünür
- [ ] Bir tarayıcı aç, PDF aç, video oynat → hepsinin üstüne yazılabiliyor
- [ ] Pencere yöneticisini aç/kapat (Cinnamon "sergi") → katman kaybolmuyor
- [ ] Başka bir çalışma alanına geç → katman orada da görünüyor
- [ ] Ekranı kilitle/çöz → katman geri geliyor
- [ ] Cinnamon tam ekran pencere aç (örn. video) → katman üstte kalıyor
- [ ] 30 dakika çizim sonrası katman yerinde mi (yığınlama zamanlayıcısı)

## 2. Geçirgenlik

- [ ] "Uygulamaya geç" düğmesi → kalem gizleniyor, mürekkep kayboluyor
- [ ] Alttaki uygulamaya dokun/tıkla → **o uygulama** çalışıyor
- [ ] Araç çubuğu hâlâ dokunulabilir
- [ ] Araç çubuğunun dışında (pasif alan) dokunma → alttaki uygulamaya gidiyor
- [ ] Tekrar "kalem" → mürekkep geri geliyor

## 3. Dokunmatik

- [ ] Tek parmakla çizim, kesintisiz (ara sıra boşluk yok)
- [ ] Parmak hareketi hızlıyken çizgi kopmuyor
- [ ] Avuç içi / kol teması çizim yapmıyor
- [ ] 20 parmak ölçeğinde çizim kayması yok
- [ ] Parmak bırakınca vuruş noktası oluşmuyor (dot çizimi var)

## 4. Kalem (stylus)

`ls /dev/input/` ve `libinput list-devices` çıktısını not edin.

- [ ] Kalem algılanıyor
- [ ] Hafif basınç = ince, sert basınç = kalın
- [ ] Çabuk çizimde çizgi uçları inceliyor (basınç düşüyor)
- [ ] Kalemin arka ucu silgi olarak çalışıyor
- [ ] Kalem yaklaşırken imleç yok oluyor, uzaklaşınca geri geliyor
- [ ] Yazarken avuç ekrana değiyor → karışma yok
- [ ] Kalem ekrandan kalkınca çizim bitmiyor

> Basınç yoksa `input/pressureEnabled=false` ile sabit genişliğe düşer —
> ayarlar penceresi M2'de geliyor, şimdilik `pen/width` değerini elle düzenleyin.

## 5. Araç çubuğu

- [ ] Sürükleniyor, bırakınca kenara yapışıyor
- [ ] Sol/sağ arasında geçiş yapabiliyor
- [ ] Dikey konumu hatırlıyor (yeniden başlatma)
- [ ] Düğmelerin çoğu tek dokunuşla, yanlışlıkla değil
- [ ] Renk döngüsü beklenen sırada
- [ ] Kalınlık döngüsü 6 kademe
- [ ] Silgi boyu döngüsü 4 kademe
- [ ] Geri al/yinele düğmeleri duruma göre pasifleşiyor

## 6. Geçmiş

- [ ] 20 çizim → 20 geri al
- [ ] Geri aldıktan sonra yeni çizim → yinelenebilir geri almalar kayboluyor
- [ ] Silgi ile silinen yer geri alınca dönüyor
- [ ] "Temizle" → geri al → tüm çizimler dönüyor
- [ ] Uzun oturumda bellek şişmiyor (`ps` ile kontrol edin)

## 7. Yakalama

- [ ] "Ekran görüntüsü" → `~/Pictures/FatihKalem/` altında PNG
- [ ] Kayıt **temiz masaüstünü** içeriyor (kendi penceresi görünmüyor)
- [ ] Üstüne çizim bindirilmiş
- [ ] Aynı saniyede iki kez → dosya adı çakışmıyor
- [ ] Ayarlardan JPEG seçiliyorsa RGB'ye çevriliyor (siyah zemin yok)
- [ ] PDF çıktısı A4 yatay ve tam sığdırılmış

## 8. Performans (4K)

| Çizim | Hedef |
|---|---|
| Üstüne gelen (hover) | Uyarı yok |
| Hızlı çizgi | Kırık çizgi yok, gecikme fark edilmez |
| Ekranı temizle | Anında |
| Geri al (tek çizim) | 100 ms altı |
| 2 saatlik ders sonrası | Kararlılık bozulmaz |

`~/.local/share/fatih-kalem-linux/` altında log yoksa konsola
`QT_LOGGING_RULES="qt.qpa.xcb.warning=true"` ile bakın.

## 9. Çok dilli

- [ ] `general/language=tr_TR` → Türkçe
- [ ] `general/language=en_US` → İngilizce
- [ ] Çeviri dışı bir ayar değiştirilse bile uygulama çalışıyor

## 10. Yeniden başlatma

- [ ] `autostart` etkinse oturum açılışında katman geliyor
- [ ] Oturumdan çıkışta temiz kapanıyor (kilit dosyası bırakmıyor)
- [ ] İkinci örnek "already running" diyip çıkıyor