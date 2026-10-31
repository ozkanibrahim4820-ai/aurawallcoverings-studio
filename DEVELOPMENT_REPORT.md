# İlk sürüm — 31 Ekim 2026

## Son güncelleme — yerel kullanım ve Printmarkt çıktı takibi

- Windows için `START_WINDOWS.bat`, Mac/Linux için `start.sh` eklendi. Python
  3.12+ ile yerel sunucuyu başlatıp kullanıcının kendi tarayıcısını açar.
  Windows başlatıcısı Linux bulut makinesinde çalıştırılamadı; doğrulanmış Windows
  testi olarak sunulmaz. `sh -n start.sh` geçti.
- Dokuz aşamalı ürün pilotu: kaynak/kanıt notu ve insan inceleme durumu; harici
  erişim yokken Etsy/Drive tamamlandı olarak işaretlenemez. Eski formdan yazma
  kontrolü ve denetim geçmişi var. Mevcut kayıtlar korunarak iki tablo eklendi.
- Printmarkt çıktı defteri: tasarım/mockup kaynak URL'leri, mockup alt metni ve
  başlık/açıklama/etiket kaydı. Aynı ürün/tür/URL yeniden kaydedilemez. SEO etiket
  sayısı/uzunluğu ve yinelenen etiket kontrolü uygulanır. Bunlar **elle kaydedilen
  çıktılardır**, Printmarkt API entegrasyonu veya dışarıdan doğrulanmış çıktı değildir.
- `python3 -m unittest discover -s tests -v`: **22 test geçti**; `node --check
  static/app.js` ve Python derleme kontrolü geçti. Aşağıdaki ilk sürümün 17 test
  sonucu tarihsel kayıttır, güncel toplam 22'dir.
- Printmarkt dashboard tekrar denendi: proxy `403 CONNECT tunnel failed`, HTTP
  hedef yanıtı yok. Kullanıcının araçların çalıştığı bildirimi alındı; bu oturum
  üzerinden tasarım/mockup/SEO araçları henüz test edilmedi. Çalışan ortamın özel
  izin listesi hâlâ boş; önce kaydedilen ağ taslağı henüz etkinleşmiş görünmüyor.
- Güncel sunucu aynı yerel portta yeniden başlatıldı. Kendi bilgisayarında açmak
  için kullanıcı kaynak ZIP'ini çıkarıp başlatıcıyı çalıştırmalı; bulut loopback
  adresi kullanıcının bilgisayarındaki loopback adresi değildir. İki veritabanı
  otomatik eşitlenmez. Kaynak ZIP'inde runtime veritabanı veya kimlik bilgisi yok.

---

## Gerçekte yapılanlar

`/workspace/aurawallcoverings-studio` altında bağımsız proje oluşturuldu.
EtsyDesk'ten uygulama kodu, kimlik bilgisi veya veritabanı alınmadı.
Eski checkout üzerinde daha önce başlayan npm kurulumu durduruldu;
`git -C /workspace/etsy-seo-app status --short` boş döndü, takip edilen kaynaklarda
değişiklik yok. Yeni proje henüz uzak Git deposuna bağlanmadı veya deploy edilmedi.

Kaynaklar: `server.py`, `domain.py`, `static/index.html`, `static/app.js`,
`static/style.css`, `tests/test_studio.py`, `README.md`, `AGENTS.md`, `.gitignore`.

Çalışan bölümler: ürün planı CRUD'nin oluşturma/güncelleme/okuma işlemleri
(silme yok), benzersiz SKU, iyimser sürüm kontrolü, kaynaklı araştırma kaydı,
Printmarkt maliyet senaryosu, 300 DPI manuel boyut hesabı, kaynak/mockup oranları,
değerlendirme ve önce/sonra geçmişi. Tüm kayıtlar SQLite'ta tutulur.
Hedef marj fiyatı marjın altına düşmemek için sente yukarı yuvarlanır.

## Doğrulama

- `python3 -m unittest discover -s tests -v`: **17 test geçti**.
- `node --check static/app.js`: geçti.
- Gerçek HTTP testleri: ürün oluşturma/okuma, mükerrer SKU çakışması, harici
  origin engeli, harici yayımlama rotasının yokluğu, kaynak/DB yoluna erişim engeli.
- Çalışan ve son kodla yeniden başlatılan yerel sunucuda `/`, `/api/health`,
  `/api/state` HTTP 200; SQLite sağlık kontrolü başarılı.
- Çalışma veritabanı boş; test ürünleri yalnızca geçici veritabanlarında kullanıldı.
- Görsel tarayıcı incelemesi veya ekran görüntüsü alınmadı; JS sözdizimi ve HTTP
  doğrulaması tarayıcı uçtan uca testi olarak sunulmaz.
- İlk sandbox denemesinde localhost soketi yasaktı. Desteklenen yürütme yetkisiyle
  aynı testler ve gerçek sunucu başarıyla çalıştırıldı.

## Ortam yapılandırması

`install_script`, `start_skill` ve şu özel ağ alan adları taslağa kaydedildi:
`printmarkt.co`, `www.etsy.com`, `aurawallcoverings.etsy.com`, `drive.google.com`.
Paket yöneticisi ön ayarları korundu. Başlatma talimatı süreçlerin yeni görevde
yeniden başlatılacağını belirtir. EtsyDesk'in mevcut depo üyeliği değiştirilmedi;
yeni dosyalar hazırlanmış dosya sistemi içindedir, uzak bir Git deposunda değildir.
Taslağın kaydedildiği doğrulandı; yayımlandığı veya yeni görevde geri yüklendiği
doğrulanmadı. Kullanıcı ortam ayarlarında gözden geçirip kaydetmeli ve ortamı
yayımlamalı. Bu, Etsy ürün yayımlaması değildir.

## Erişim sınırları ve eksik işler

Printmarkt dashboard HEAD isteği mevcut proxy'de `403 CONNECT tunnel failed`
aldı. Bu, hesaplayıcıdan gelen bir giriş hatası veya fiyat sonucu değildir;
mevcut ağ politikasında erişim doğrulanamadı. Taslak ağ değişikliği çalışan
ortama uygulanmış sayılmaz. Sonraki adımda önce ağ erişimi tekrar kontrol edilmeli.

Etsy, Drive, Printmarkt ve otomatik çalıştırıcı bağlı değil. Yetkili mağaza
verisi, istatistik, eski SKU, dosya, kargo profili, sabit açıklama, video ve ücret
tablosu okunmadı. API tek bağlantı yöntemi veya ön koşul sayılmıyor. Yeni API
anahtarı istenmedi. Güncel Etsy politika ve ücretleri doğrulanmadı.

Ürün planları gerçek tasarım veya listing değildir. Fiyatlar doğrulanmamış
senaryodur; dosya kontrolü elle girilen boyutlardan ibarettir. Gerçek repeat,
3×3 görüntü, keskinlik, upscale ve benzerlik analizi yoktur. Tasarım, mockup,
İngilizce SEO, gerçek Etsy taslağı ve Drive yüklemesi üretilmedi. Listing ID,
atanmış pilot SKU veya Drive çıktı bağlantısı yoktur. Üç ürünlük pilot ve 15–20
ürünlük üretim hattı henüz tamamlanmadı.

## Sonraki sıra

1. Ortam taslağını etkinleştirme sonrası Printmarkt/Etsy/Drive erişimini tekrar
   doğrula; mevcut yetkili oturum veya desteklenen bağlantıyı belirle.
2. Önce mağaza ve Drive envanterini okuyup mükerrerleri ayır; fiyat ve baskı
   şartlarını kaynak/tarih ve gider kapsamıyla kaydet.
3. Gerçek dosya denetimi, repeat incelemesi, 10 tutarlı mockup ve satıcı yaratıcı
   katkısı onayıyla pilotu geliştir.
4. Yalnızca taslak yazabilen, işlem tekrarını önleyen Etsy adaptörü ve yalnızca
   bitmiş baskı dosyası yükleyen Drive adaptörü; işlemlerden sonra geri okuma.
5. Kaynaklı performans verisi ve öneri/uygulama/sonuç ayrımıyla satış analizi.

Yerel prototipte giriş sistemi yoktur; yalnızca loopback üzerinde çalıştırılır,
internete açılmamıştır. Hiçbir Etsy aktif ürünü, reklam, indirim, fiyat veya mağaza
ayarı değiştirilmedi. Abonelik satın alınmadı, TinyFish kullanılmadı.
