"""Source-attributed manual performance reports; explainable, unapplied advice."""
from datetime import date
import re
from domain import ValidationError, number, text, money

METRICS = ("visits", "views", "favorites", "orders", "revenue", "ad_spend", "ad_revenue", "etsy_search_visits", "social_visits")
COUNTS = {"visits", "views", "favorites", "orders", "etsy_search_visits", "social_visits"}


def validate_report(data):
    result = {key: text(data, key, limit) for key, limit in (("product_id", 100), ("listing_id", 20), ("source", 1000), ("period_start", 10), ("period_end", 10), ("currency", 3))}
    if not re.fullmatch(r"[0-9]{1,20}", result["listing_id"]):
        raise ValidationError("Gerçek Etsy listing ID yalnızca rakam içermeli.")
    try:
        start, end = date.fromisoformat(result["period_start"]), date.fromisoformat(result["period_end"])
    except ValueError:
        raise ValidationError("Rapor tarihleri YYYY-MM-DD olmalı.")
    if start > end or end > date.today():
        raise ValidationError("Tarih aralığı geçersiz veya gelecekte.")
    if not re.fullmatch(r"[A-Za-z]{3}", result["currency"]):
        raise ValidationError("Üç harfli para birimi gerekli.")
    result["currency"] = result["currency"].upper()
    result["notes"] = text(data, "notes", 10000, required=False)
    for key in METRICS:
        if data.get(key) is None or data[key] == "":
            result[key] = None
        else:
            value = number(data, key, maximum=10**12)
            if key in COUNTS and value != int(value):
                raise ValidationError(f"Tam sayı gerekli: {key}")
            result[key] = int(value) if key in COUNTS else money(value)
    if all(result[key] is None for key in METRICS):
        raise ValidationError("En az bir gerçek metrik girilmeli; bilinmeyenler boş kalmalı.")
    return result


def analyze_report(report, today=None):
    today = today or date.today()
    age = (today - date.fromisoformat(report["period_end"])).days
    visits, orders = report["visits"], report["orders"]
    insights = []

    def advice(code, reason, action, priority="review"):
        insights.append(dict(code=code, reason=reason, action=action, priority=priority,
                             evidence="rule_based_suggestion", applied=False))

    if age > 30:
        advice("stale", f"Rapor dönemi {age} gün önce bitti.", "Güncel raporla karşılaştırın; eski rakamları bugünün performansı olarak yorumlamayın.", "data")
    if visits is None or orders is None:
        advice("missing_conversion", "Ziyaret veya sipariş verisi eksik.", "Aynı dönemin ziyaret ve sipariş sayısını girin; dönüşüm şu an hesaplanamaz.", "data")
    elif visits < 100:
        advice("small_sample", f"Dönemde {visits} ziyaret kaydedilmiş.", "Örneklem sınırlı; tasarımın satmayacağı sonucuna varmayın. 100 ziyaret yalnızca panelin inceleme eşiğidir, istatistiksel kesinlik sınırı değildir.", "data")
    if visits is not None and visits >= 100 and orders == 0:
        advice("visits_without_orders", f"{visits} ziyaret, 0 sipariş bildirilmiş.", "İlk görsel, numune sunumu, ölçü/malzeme açıklığı ve kargo dahil toplam fiyatı inceleyin. Tek bir neden varsaymayın.", "high")
    if visits == 0:
        advice("no_visits", "Bu rapor döneminde 0 ziyaret bildirilmiş.", "Kaynağı ve tarih aralığını doğrulayın; ardından başlık, kategori, özellik ve arama görünürlüğünü inceleyin.")
    if visits == 0 and orders is not None and orders > 0:
        advice("inconsistent", "0 ziyaretle pozitif sipariş sayısı bildirilmiş.", "Ziyaret ve sipariş raporlarının aynı kapsam ve döneme ait olduğunu doğrulayın.", "data")
    spend, ad_revenue = report["ad_spend"], report["ad_revenue"]
    if spend is not None and spend > 0:
        if ad_revenue is None:
            advice("missing_ad_attribution", "Reklam gideri var, reklama atfedilen gelir eksik.", "Toplam geliri reklam geliri yerine kullanmayın. Etsy Ads dönem ve atıf verisini doğrulayın.", "data")
        advice("profit_before_ads", "Reklam harcaması bildirilmiş; gerçekleşen üretim/kargo/ücret giderleri bu raporda yok.", "Bütçe değiştirmeden önce sipariş ve varyasyon bazında gerçek kârlılığı doğrulayın.")
    return {"source_kind": "manual_report", "external_verified": False,
            "age_days": age, "stale": age > 30,
            "conversion_pct": round(orders / visits * 100, 2) if visits and orders is not None else None,
            "ad_roas": round(ad_revenue / spend, 2) if spend and ad_revenue is not None else None,
            "missing_fields": [key for key in METRICS if report[key] is None],
            "profit": None, "recommendations": insights,
            "note": "Kaynak kullanıcı raporu; bağlantıdan doğrulanmadı. Dönüşüm sipariş/ziyaret, ROAS yalnız reklama atfedilen gelir/reklam gideridir. Öneriler uygulanmadı; rapor dönemleri toplanmaz."}
