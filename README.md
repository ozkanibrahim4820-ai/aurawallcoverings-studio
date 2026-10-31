# AuraWallCoverings Studio

Bağımsız, yerel geliştirme prototipi. EtsyDesk kodu veya veritabanı kullanılmaz.
Python 3.12+ standart kütüphanesiyle çalışır; paket veya abonelik gerekmez.

## Kendi Windows bilgisayarınızda açma

Proje deposu: https://github.com/ozkanibrahim4820-ai/aurawallcoverings-studio
GitHub'da `Code` → `Download ZIP` seçeneğini kullanın. Özel depoya erişmek için
deponun sahibi olan GitHub hesabınızda oturum açmanız gerekebilir.

Kaynak ZIP paketini indirip bir klasöre çıkarın. İçindeki `START_WINDOWS.bat`
dosyasına çift tıklayın. Python 3.12+ kuruluysa sunucu başlar ve tarayıcı otomatik
açılır. Python yoksa başlatıcı kurulum adresini gösterir; Python kurulumunda
“Add Python to PATH” seçeneğini işaretleyin. Sunucu penceresi açık kalmalı.
Kapatmak için pencerede Ctrl+C kullanın.

Mac/Linux: proje klasöründe `sh start.sh` çalıştırın.
Bu başlatıcılar bulut makinesi yerine sizin bilgisayarınızda uygulamayı açar.
Windows başlatıcısı bu Linux ortamında çalıştırılarak doğrulanmadı.
Kendi makinenizin verileri bulutla otomatik eşitlenmez. Güncellemelerde `data/`
klasörünü koruyun; kaynak paketi kullanıcı verisi içermez. Yeni kaynak sürümlerini
çalışma klasörüne alırken sunucuyu kapatın ve mevcut veriyi yedekleyin.

## Çalıştırma

```sh
cd /workspace/aurawallcoverings-studio
python3 server.py --port 8787
```

Sunucu yalnızca 127.0.0.1 adresini dinler. Port 8787 üzerinden yerel tarayıcı
erişimi içindir. Kullanıcı kimlik doğrulaması yoktur; internete açmayın.
Başka makinede `/workspace/aurawallcoverings-studio` yerine proje dizinini kullanın.

```sh
python3 -m unittest discover -s tests -v
node --check static/app.js
```

`GET /api/health`: SQLite sorgusu ve yerel uygulama kontrolü.
`GET /api/state`: en son 500 ürün, araştırma, değerlendirme ve değişiklik kaydı.
SQLite tüm kayıtları saklar; arayüz ve state API'si her bölümde en son 500 kaydı gösterir.
Boş veritabanıyla başlar; örnek ürünler gerçek veri olarak eklenmez.

## İlk sürüm

- Ürün planı oluşturma/düzenleme, büyük-küçük harfe duyarsız benzersiz SKU.
- Sürüm kontrolü: eski form güncel kaydın üzerine yazamaz.
- Kaynak, gözlem tarihi, ölçülen/tahmin/eksik ayrımıyla araştırma defteri.
- Printmarkt varyasyon senaryoları: üretim, toplu ve iç kargo, gümrük/vergi,
  diğer gider, listeleme, ödeme ve reklam giderleri. Her maliyet açıkça girilir.
- İndirim sonrası kâr, ayrı ücret matrahları ve hedef marj için liste fiyatı.
  Alıcıdan tahsil edilen vergi gelir sayılmaz; vergi dahil ücretler ayrıca hesaplanır.
  Tutarlar aynı para biriminde olmalı; kur dönüşümü yapılmaz.
- Elle girilen gerçek piksel ve fiziksel ölçülerden 300 DPI kontrolü; kaynak/mockup
  oranı kontrolü. Seamless boyutu toplam duvar değil, tek tekrar ölçüsüdür.
- `Tasarım dosyaları` ekranında gerçek PNG/JPEG (en fazla 20 MB) yükleme.
  Kaynak değişmez; dosya başlığından piksel boyutu okunur, SHA-256 ile saklanır.
  Aynı ürün/tür/dosya yeniden yüklenmez; aynı kaynak başka ürüne de atanamaz.
  Bu yalnızca aynı baytların kontrolüdür, görsel benzerlik/özgünlük garantisi değil.
- Seamless kaynak için tarayıcıda küçültülmüş 3×3 tekrar önizlemesi. Kaynak dosya
  değiştirilmez, baskı dosyası veya upscale üretilmez. 40 MP üzeri dosyalarda
  tarayıcı bellek tüketimi için önizleme kapalıdır; başlık ölçümü kullanılabilir.
- `Baskı kontrolü` ekranında yüklenmiş dosyayı seçince ölçüler dosya kaydından
  alınır. Sunucu istemcinin farklı bir piksel boyutu göndermesine güvenmez.
  Piksel kod çözümü, netlik, renk profili, EXIF yönü ve repeat kalitesi otomatik
  doğrulanmış sayılmaz; baskıya hazır onayı verilmez.
- Önce/sonra değişiklik geçmişi, kalıcı SQLite, yinelenen hesap ve SKU kontrolü.
- Gerçek bağlantı durumları: bağlı olmayan hizmetler başarılı gösterilmez.
- Dokuz aşamalı pilot kontrolü: kanıt/not ve insan inceleme durumu. Bağlantı
  olmadan Etsy/Drive tamamlandı olarak işaretlenemez; kayıt otomasyon çalıştırmaz.
- Printmarkt çıktı defteri: gerçek tasarım/mockup URL'lerini ve kopyalanan SEO
  başlık/açıklama/etiketlerini ürüne kaydeder. Mockuplar için alt metin gerekir.
  Kayıtlı mockup bağlantısı sayısını 10 hedefiyle gösterir; bunlar dosya incelemesi
  veya otomatik üretilen mockuplar değildir. SEO'da 140 karakter başlık, 13 benzersiz
  etiket ve etiket başına 20 karakter sınırı uygulanır. Metinlerin güncel politika,
  malzeme ve mağaza sabit açıklaması açısından insan incelemesi ayrıca gerekir.

## Sınırlar

Bu sürüm Etsy/Drive/Printmarkt'a bağlanmaz; veri çekmez, AI görseli üretmez,
mockup oluşturmaz, dışarı dosya yüklemez ve ürün yayımlamaz. Etsy taslağı yoktur;
listing ID veya Drive bağlantısı üretilmez. Etsy kural ve ücretleri çevrimiçi
doğrulanmadı; formdaki oranlar kullanıcı tarafından girilir. Tüm fiyatlar
doğrulanmamış senaryo olarak etiketlenir; 30 günden eski kaynak uyarılır.
Dosya netliği, repeat/kenar ve 3×3 önizlemesinin insan incelemesi, satıcı katkısı, benzerlik ve 10 mockup
incelemesi insan kontrolü bekler; baskıya hazır onayı otomatik verilmez.
SKU kontrolü tasarımsal veya hukuki özgünlük garantisi değildir.

## Veriyi koruma

Çalışma kayıtları `data/studio.sqlite3` içinde, kaynak koddan ayrı ve Git dışında.
Yedekleme için SQLite backup API'sini kullanın; açık veritabanını körlemesine
üzerine kopyalamayın. Yerel kayıtlar kimlik bilgisi kasası değildir. Şifre veya API
anahtarı notlara, kaynak URL'lerine veya formlara girilmemeli.
Testler geçici veritabanı kullanır, gerçek çalışma kayıtlarına dokunmaz.
Yüklenen kaynak dosyaları da `data/assets/` altındadır; güncelleme ve yedekleme
sırasında tüm `data/` klasörünü koruyun. SQLite yedeği tek başına görsel dosyalarını
içermez. Kaynak ZIP ve Git deposu kullanıcı dosyalarını içermez.

## İsteğe bağlı gerçek tarayıcı kontrolü

Bulut geliştirme ortamında kurulu Chromium ve Playwright Python ile
`python3 scripts/browser_check.py` çalıştırıldı. Geçici veritabanında ürün,
gerçek PNG yükleme, dokuz tekrardaki 36 renk örneği, gerçek JPEG başlık ölçümü ve
dosyadan 300 DPI formuna aktarım doğrulandı. Bunlar uygulamanın çalışma zamanı
bağımlılığı değildir; kullanıcı bilgisayarına kurulmaları gerekmez.

## Sonraki entegrasyonlar

1. Yetkili mağaza oturumu/bağlantısıyla AuraWallCoverings kimliği ve mevcut
   ürün/taslakların okunması; eski SKU ve dosyalarla mükerrer kontrolü.
2. Printmarkt hesaplayıcısından tarihli, malzeme/ölçü bazlı maliyet kanıtı;
   ücret, taşıma ve gümrük sorumluluğu doğrulaması.
3. Yetkili Drive klasörü ve yalnızca tamamlanmış baskı dosyası yükleme.
4. Tasarım/tekrar/gerçek upscale ve 10 mockup inceleme akışı.
5. Yalnızca Etsy taslağı oluşturma, işlem anahtarı ve geri okuma doğrulaması.
6. Ürün başına gerçek trafik/reklam/sipariş verileri, önce/sonra ölçümü ve Pinterest
   içerik planı. Plan/kuyruk kaydı çalıştırılmış görev sayılmaz.

Önce üç gerçek ürünlük pilot uçtan uca doğrulanır. Sonra aynı kayıt yapısı 15–20
ürünlük partiye genişletilir. Otomatik yayımlama, aktif ürün/fiyat/reklam değişikliği,
TinyFish ve abonelik satın alma kapsam dışıdır.
