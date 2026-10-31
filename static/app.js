"use strict";
let state;
const $ = (q) => document.querySelector(q);
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const date = value => new Date(value).toLocaleString("tr-TR");
const labels = {files:"Tasarım dosyaları",outputs:"Printmarkt çıktıları",pilot:"Pilot kontrolü",overview:"Genel görünüm",products:"Ürünler & pilot",research:"Araştırma defteri",pricing:"Maliyet & kâr",quality:"Baskı kontrolü",activity:"İşlem geçmişi"};
const evidence = {measured:"Ölçülen veri",estimate:"Tahmin / iddia",missing:"Eksik veri"};
function message(value) { $("#message").textContent = value; }
async function api(path, method="GET", data) {
  const res = await fetch(path, {method, headers:{"Content-Type":"application/json"}, ...(data ? {body:JSON.stringify(data)} : {})});
  const json = await res.json(); if(!res.ok) throw new Error(json.error || "İşlem başarısız."); return json;
}
function navigate(view) {
  if (!labels[view]) return;
  document.querySelectorAll(".view").forEach(el => el.hidden = el.id !== view);
  document.querySelectorAll("nav button").forEach(el => el.classList.toggle("active", el.dataset.view === view));
  $("#page-title").textContent = labels[view];
}
document.addEventListener("click", e => { const button=e.target.closest("[data-view]"); if(button) navigate(button.dataset.view); });
function empty(text) { return `<div class="empty">${escapeHTML(text)}</div>`; }
function productName(id) { return state.products.find(p=>p.id===id)?.title || id; }
function render() {
  $("#metrics").innerHTML = [[state.products.length,"Yerel ürün planı"],[state.research.length,"Araştırma kaydı"],[state.evaluations.filter(e=>e.kind==="pricing").length,"Fiyat senaryosu"],["—","Etsy taslakları / bağlantı yok"]].map(([n,label])=>`<div class="metric"><strong>${n}</strong><span>${label}</span></div>`).join("");
  $("#connections").innerHTML = [["Etsy","Bağlı değil"],["Google Drive","Bağlı değil"],["Printmarkt hesaplayıcı","Bağlı değil"],["Otomatik çalıştırıcı","Kurulu değil"]].map(([name,status])=>`<div class="connection"><span>${name}</span><span class="badge warn">${status}</span></div>`).join("");
  $("#product-list").innerHTML = state.products.map(p=>`<article class="product-card"><div class="product-art">Görsel henüz oluşturulmadı</div><h3>${escapeHTML(p.title)}</h3><small>${escapeHTML(p.sku)} · ${escapeHTML(p.kind)}</small><p>${escapeHTML(p.notes || "Yaratıcı yönlendirme bekleniyor.")}</p><span class="badge warn">Yalnızca plan</span><p class="muted">Mockup: doğrulanmadı · Etsy: bağlı değil<br>Baskı dosyası: doğrulanmadı · Drive: bağlı değil</p><button class="secondary" data-edit="${p.id}">Planı düzenle</button></article>`).join("") || empty("Henüz ürün yok. Mükerrer kontrolünden sonra üç ürünlük pilotu planlayın.");
  document.querySelectorAll(".product-select").forEach(select=>{const old=select.value; select.innerHTML='<option value="">Ürün seçin</option>'+state.products.map(p=>`<option value="${p.id}">${escapeHTML(p.sku)} — ${escapeHTML(p.title)}</option>`).join(""); select.value=old;});
  $("#research-list").innerHTML=state.research.map(r=>`<article class="entry"><span class="badge">${evidence[r.evidence]}</span><time>${escapeHTML(r.observed_on)}</time><h3>${escapeHTML(r.title)}</h3><a href="${escapeHTML(r.source)}" target="_blank" rel="noopener noreferrer">${escapeHTML(r.source)}</a><p>${escapeHTML(r.notes)}</p></article>`).join("") || empty("Araştırma kaydı yok. Otomatik araştırma henüz bağlı değil.");
  for(const kind of ["pricing","quality"]) $("#"+kind+"-history").innerHTML=state.evaluations.filter(e=>e.kind===kind).map(e=>`<article class="entry"><h3>${escapeHTML(productName(e.product_id))}${kind==="pricing"?" · "+escapeHTML(e.inputs.variation || "Varyasyon belirtilmedi"):""}</h3><time>${date(e.created_at)}</time><span class="badge warn">${kind==="pricing"?"Doğrulanmamış senaryo":e.result.input_evidence==="file_header"?"Dosya başlığından ölçü":"Elle girilen ölçüler"}</span><details><summary>Girdiler ve hesap sonucu</summary><pre>${escapeHTML(JSON.stringify({inputs:e.inputs,result:e.result},null,2))}</pre></details></article>`).join("");
  $("#audit-list").innerHTML=state.audits.map(a=>`<article class="entry"><strong>${escapeHTML(a.event)}</strong><time>${date(a.created_at)}</time><details><summary>Önce / sonra</summary><pre>${escapeHTML(JSON.stringify({before:a.before_json?JSON.parse(a.before_json):null,after:JSON.parse(a.after_json)},null,2))}</pre></details></article>`).join("") || empty("Henüz işlem yok.");
}
async function refresh() {state=await api("/api/state");render();renderPilot();renderOutputs();renderAssets();}
$("#refresh").onclick=()=>refresh().then(()=>message("Yerel kayıtlar yenilendi. Harici veri çekilmedi.")).catch(e=>message(e.message));
function editor(product) {
 const form=$("#product-form");form.reset(); for(const key of ["id","version","title","sku","kind","notes"]) form.elements[key].value=product?.[key] ?? (key==="kind"?"seamless":"");
 $("#product-editor").hidden=false; $("#product-form-title").textContent=product?"Ürün planını düzenle":"Yeni ürün planı";form.elements.title.focus();
}
$("#add-product").onclick=()=>editor(); $("#cancel-product").onclick=()=>$("#product-editor").hidden=true;
$("#product-list").onclick=e=>{const button=e.target.closest("[data-edit]");if(button) editor(state.products.find(p=>p.id===button.dataset.edit));};
const costFields = [["price","Liste fiyatı"],["shipping_charged","Alıcıdan alınan kargo"],["buyer_tax","Alıcıdan tahsil edilen vergi"],["discount_pct","İndirim (%)",100],["production","Üretim"],["bulk_shipping","Türkiye → ABD / toplu taşıma payı"],["domestic_shipping","ABD içi kargo"],["customs_tax","Satıcıya düşen vergi / gümrük"],["other_costs","Diğer giderler"],["listing_fee","Listeleme ücreti payı"],["payment_fixed","Sabit ödeme kesintisi"],["ads_fixed","Sabit reklam gideri payı"],["transaction_pct","İşlem kesintisi (%)",100],["payment_pct","Ödeme kesintisi (%)",100],["ads_pct","Yüzdesel reklam kesintisi (%)",100],["target_margin_pct","Hedef kâr marjı (%)",99]];
$("#cost-fields").innerHTML=costFields.map(([key,label,max])=>`<label>${label}<input name="${key}" type="number" min="${key==="price"?"0.01":"0"}" step="any" ${max!==undefined?`max="${max}"`:""} required></label>`).join("");
$("#tax-fields").innerHTML=[["transaction_on_tax","İşlem ücretinde alıcı vergisi"],["payment_on_tax","Ödeme ücretinde alıcı vergisi"],["ads_on_tax","Reklam ücretinde alıcı vergisi"]].map(([key,label])=>`<label>${label}<select name="${key}" required><option value="">Matrahı doğrulayın</option><option value="false">Dahil değil</option><option value="true">Dahil</option></select></label>`).join("");
async function submit(form, fn) { const button=form.querySelector('[type="submit"]');button.disabled=true;message("");try {await fn();} catch(e){message(e.message);} finally {button.disabled=false;} }
$("#product-form").onsubmit=e=>{e.preventDefault();const form=e.target;submit(form,async()=>{const data=Object.fromEntries(new FormData(form));const id=data.id;delete data.id;data.version=Number(data.version);await api(id?"/api/products/"+id:"/api/products",id?"PATCH":"POST",data);$("#product-editor").hidden=true;await refresh();message("Ürün planı kaydedildi. Etsy’de işlem yapılmadı.");});};
$("#research-form").onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{await api("/api/research","POST",Object.fromEntries(new FormData(e.target)));e.target.reset();await refresh();message("Kaynaklı araştırma kaydı eklendi.");});};
$("#pricing-form").onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const inputs=Object.fromEntries(new FormData(e.target));const product_id=inputs.product_id;delete inputs.product_id;for(const key of ["payment_on_tax","transaction_on_tax","ads_on_tax"])inputs[key]=inputs[key]==="true";const {result:r}=await api("/api/pricing","POST",{product_id,inputs});const box=$("#pricing-result");box.hidden=false;box.innerHTML=`<span class="badge warn">Doğrulanmamış fiyat senaryosu${r.stale?" · Kaynak 30 günden eski":""}</span><div class="result-grid">${[[r.revenue,"İndirim sonrası gelir"],[r.total_cost,"Toplam gider"],[r.profit,"Tahmini kâr"],[r.margin_pct,"Marj (%)"],[r.target_price,"Hedef marj için liste fiyatı"]].map(([v,l])=>`<div><strong>${v===null?"Hesaplanamıyor":escapeHTML(v)+" "+(l.includes("(%)")?"%":escapeHTML(r.currency))}</strong><span>${l}</span></div>`).join("")}</div><p>${escapeHTML(r.note)}</p>`;await refresh();});};
$("#quality-form").onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const inputs=Object.fromEntries(new FormData(e.target));const product_id=inputs.product_id;delete inputs.product_id;if(inputs.asset_id)inputs.kind=state.assets.find(a=>a.id===inputs.asset_id)?.kind;const {result:r}=await api("/api/quality","POST",{product_id,inputs});const box=$("#quality-result");box.hidden=false;box.innerHTML=`<span class="badge warn">Baskıya hazır onayı verilmedi</span><div class="result-grid"><div><strong>${r.required_width_px} × ${r.required_height_px}</strong><span>Gerekli minimum piksel</span></div><div><strong>${r.effective_dpi}</strong><span>Hesaplanan efektif DPI</span></div><div><strong>${r.ratio_ok?"Uygun":"Uygun değil"}</strong><span>Kaynak / mockup oranı</span></div><div><strong>${r.resolution_ok?"Yeterli":"Yetersiz"}</strong><span>300 DPI piksel gereksinimi</span></div></div><p>${escapeHTML(r.note)}</p>`;await refresh();});};
const pilotLabels = {duplicates:"Benzerlik / mükerrer kontrolü",research:"Pazar araştırması",creative:"Yaratıcı yön ve satıcı katkısı",print:"Baskı, repeat ve 3×3 kontrolü",mockups:"10 mockup incelemesi",pricing:"Varyasyon maliyeti",seo:"İngilizce SEO",etsy:"Etsy taslağı / geri okuma",drive:"Drive baskı dosyası"};
const pilotStatuses = {not_started:"Başlanmadı",in_progress:"Çalışılıyor",blocked:"Engelli",reviewed:"İnsan incelemesi kaydedildi"};
function currentPilotCheck() {return state.pilot_checks.find(c=>c.product_id===$("#pilot-product").value && c.step===$("#pilot-step").value);}
function loadPilotForm() {
  const check=currentPilotCheck();
  $("#pilot-status").value=check?.status || "not_started";
  $("#pilot-evidence").value=check?.evidence || "";
  $("#pilot-form").elements.expected_updated_at.value=check?.updated_at || "";
  $("#pilot-status").querySelector('[value="reviewed"]').disabled=["etsy","drive"].includes($("#pilot-step").value);
}
function renderPilot() {
  const productId=$("#pilot-product").value;
  if(!productId) {$("#pilot-list").innerHTML=empty("Bir ürün seçerek dokuz pilot adımını takip edin.");loadPilotForm();return;}
  $("#pilot-list").innerHTML=Object.entries(pilotLabels).map(([step,label])=>{
    const check=state.pilot_checks.find(c=>c.product_id===productId&&c.step===step);
    return `<article class="entry"><h3>${label}</h3><span class="badge ${check?.status==="reviewed"?"":"warn"}">${pilotStatuses[check?.status||"not_started"]}</span>${check?`<time>${date(check.updated_at)}</time><p>${escapeHTML(check.evidence)}</p><small class="muted">Yerel insan kaydı · Harici işlem doğrulaması değildir</small>`:""}</article>`;
  }).join("");
  loadPilotForm();
}
$("#pilot-product").onchange=renderPilot;
$("#pilot-step").onchange=loadPilotForm;
$("#pilot-form").onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const data=Object.fromEntries(new FormData(e.target));await api("/api/pilot-checks","POST",data);await refresh();message("Pilot inceleme notu kaydedildi. Harici işlem yapılmadı.");});};
function outputRole() {
  const role=$("#output-role").value;
  $("#output-mockup").hidden=role!=="mockup";$("#output-seo").hidden=role!=="seo";
  const form=$("#output-form");for(const key of ["alt_text","title","description","tags"]) form.elements[key].required=(key==="alt_text"?role==="mockup":role==="seo");
}
function renderOutputs() {
  const roleLabels={design:"Tasarım kaynağı",mockup:"Mockup",seo:"SEO metni"};
  $("#output-list").innerHTML=state.products.map(p=>{
    const outputs=state.outputs.filter(o=>o.product_id===p.id);
    const count=outputs.filter(o=>o.role==="mockup").length;
    return `<article class="entry"><h3>${escapeHTML(p.title)}</h3><p class="muted">${count} / 10 mockup bağlantısı kaydedildi · Dosya/ölçek/renk doğrulaması yapılmadı</p>${outputs.map(o=>`<div class="entry"><span class="badge warn">${roleLabels[o.role]} · Elle kaydedildi</span><time>${date(o.created_at)}</time><p><a href="${escapeHTML(o.reference)}" target="_blank" rel="noopener noreferrer">Kaynak / çıktı bağlantısını aç ↗</a></p>${o.role==="seo"?`<details><summary>SEO içeriğini gör</summary><h3>${escapeHTML(o.payload.title)}</h3><p>${escapeHTML(o.payload.description)}</p><p>${escapeHTML(o.payload.tags.join(", "))}</p></details>`:""}${o.role==="mockup"?`<p>Alt metin: ${escapeHTML(o.payload.alt_text)}</p>`:""}<p>${escapeHTML(o.payload.notes)}</p></div>`).join("")||"<p>Henüz çıktı kaydı yok.</p>"}</article>`;
  }).join("") || empty("Önce bir ürün planı oluşturun. Ardından Printmarkt çıktısını o ürüne kaydedin.");
}
$("#output-role").onchange=outputRole;
$("#output-form").onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const data=Object.fromEntries(new FormData(e.target));if(data.role==="seo")data.tags=data.tags.split(",").map(t=>t.trim()).filter(Boolean);await api("/api/outputs","POST",data);e.target.reset();outputRole();await refresh();message("Printmarkt çıktı kaydı eklendi. Dosya veya SEO haricen doğrulanmadı; Etsy’de işlem yapılmadı.");});};
function renderAssets() {
  $("#asset-list").innerHTML=state.assets.map(a=>`<article class="entry"><h3>${escapeHTML(a.filename)}</h3><p>${escapeHTML(productName(a.product_id))} · ${escapeHTML(a.kind)} · ${a.metadata.width_px} × ${a.metadata.height_px} px · ${(a.size_bytes/1048576).toFixed(2)} MB</p><span class="badge warn">Dosya başlığı okundu · Baskı onayı değil</span><p class="muted">${escapeHTML(a.metadata.orientation_note)}</p><details><summary>Dosya bütünlüğü / SHA-256</summary><pre>${escapeHTML(a.sha256)}</pre></details>${a.metadata.preview_allowed?`<p><a href="/assets/${a.id}" target="_blank" rel="noopener">Orijinali yerelde aç</a></p>${a.kind==="seamless_source"?`<button type="button" class="secondary" data-repeat="${a.id}">3×3 tekrar incele</button>`:""}`:'<p class="muted">40 megapiksel üzeri görsel: tarayıcı bellek sınırı için önizleme kapalı. Ölçü hesabı kullanılabilir.</p>'}</article>`).join("") || empty("Dosya yüklenmedi. Önce ürün planı oluşturup gerçek tasarım dosyanızı ekleyin.");
  const form=$("#quality-form"), old=$("#quality-asset").value;
  $("#quality-asset").innerHTML='<option value="">Elle ölçü gir</option>'+state.assets.filter(a=>a.product_id===form.elements.product_id.value).map(a=>`<option value="${a.id}">${escapeHTML(a.filename)} · ${a.metadata.width_px} × ${a.metadata.height_px}</option>`).join("");
  $("#quality-asset").value=old;
  if(!$("#quality-asset").value) $("#quality-asset").value="";
  applyAssetDimensions();
}
function applyAssetDimensions() {
  const asset=state.assets.find(a=>a.id===$("#quality-asset").value), form=$("#quality-form");
  for(const field of ["width_px","height_px"]) {
    form.elements[field].readOnly=!!asset;
    if(asset) form.elements[field].value=asset.metadata[field];
  }
  form.elements.kind.disabled=!!asset;
  if(asset) form.elements.kind.value=asset.kind;
}
$("#quality-asset").onchange=applyAssetDimensions;
$("#quality-form").elements.product_id.onchange=renderAssets;
$("#asset-form").onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{
  const form=e.target,file=form.elements.file.files[0];if(!file||file.size>20*1024*1024)throw new Error("En fazla 20 MB PNG/JPEG seçin.");
  const base64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",")[1]);reader.onerror=()=>reject(new Error("Dosya okunamadı."));reader.readAsDataURL(file);});
  const result=await api("/api/assets","POST",{product_id:form.elements.product_id.value,kind:form.elements.kind.value,filename:file.name,base64});
  form.elements.file.value="";await refresh();message(result.reused?"Bu dosya zaten kayıtlı; ikinci kopya oluşturulmadı.":"Dosya değişmeden yerel arşive kaydedildi. Baskı onayı veya Drive yüklemesi yapılmadı.");
});};
$("#asset-list").onclick=e=>{const button=e.target.closest("[data-repeat]");if(!button)return;const asset=state.assets.find(a=>a.id===button.dataset.repeat);if(!asset||!asset.metadata.preview_allowed)return;
  const image=new Image();image.onload=()=>{const canvas=$("#repeat-canvas"),scale=300/Math.max(image.naturalWidth,image.naturalHeight),w=Math.max(1,Math.round(image.naturalWidth*scale)),h=Math.max(1,Math.round(image.naturalHeight*scale));canvas.width=w*3;canvas.height=h*3;const ctx=canvas.getContext("2d");ctx.clearRect(0,0,canvas.width,canvas.height);for(let y=0;y<3;y++)for(let x=0;x<3;x++)ctx.drawImage(image,x*w,y*h,w,h);$("#repeat-review").hidden=false;$("#repeat-review").scrollIntoView({behavior:"smooth"});};
  image.onerror=()=>message("Tarayıcı görselin piksel verisini açamadı. Başlık ölçüsü tek başına dosyanın sağlam olduğunu garanti etmez.");image.src="/assets/"+asset.id;
};
outputRole();
refresh().catch(e=>message("Veriler yüklenemedi: "+e.message));
