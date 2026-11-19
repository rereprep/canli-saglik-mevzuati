(function(){
  "use strict";
  var kok = (document.querySelector('link[rel=stylesheet]').getAttribute('href')||'').split('assets/stil.css')[0];
  var TUR = {kanun:"Kanun",cbk:"Cumhurbaşkanlığı Kararnamesi",khk:"Kanun Hükmünde Kararname",bkk:"Bakanlar Kurulu Kararı",ck:"Cumhurbaşkanı Kararı",tuzuk:"Tüzük",yonetmelik:"Yönetmelik",yonerge:"Yönerge",genelge:"Genelge",teblig:"Tebliğ",protokol:"Protokol",yazi:"Resmî Yazı"};
  var HARF = {"ç":"c","ğ":"g","ı":"i","ö":"o","ş":"s","ü":"u","â":"a","î":"i","û":"u"};
  function sade(s){return (s||"").toLocaleLowerCase("tr").replace(/[çğıöşüâîû]/g,function(c){return HARF[c];}).normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^0-9a-z]+/g," ").trim();}
  function e(s){return String(s||"").replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function kacis(s){return s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");}
  function tr(iso){var m=/(\d{4})-(\d{2})-(\d{2})/.exec(iso||"");return m?m[3]+"."+m[2]+"."+m[1]:(iso||"");}

  var suz=document.getElementById("liste-suz");
  var mg0=document.getElementById("mulga-goster");
  var lb=document.getElementById("liste-birim");
  var suzUygula=function(){var q=suz?sade(suz.value):"",mul=!mg0||mg0.checked,br=lb?lb.value:"",say=0,tum=0;document.querySelectorAll("table.liste tbody tr").forEach(function(tr){tum++;
    var gor=(!q||sade(tr.textContent).indexOf(q)>=0)&&(mul||!tr.hasAttribute("data-mulga"))&&(!br||("|"+(tr.getAttribute("data-birim")||"")+"|").indexOf("|"+br+"|")>=0);
    tr.style.display=gor?"":"none";if(gor)say++;});
    var bl=document.getElementById("liste-bilgi");if(bl)bl.textContent=(q||br||!mul)?(say+" / "+tum+" kayıt gösteriliyor"):"";};
  if(lb){var bp=new URLSearchParams(location.search).get("birim");if(bp){for(var bi=0;bi<lb.options.length;bi++)if(lb.options[bi].value===bp)lb.value=bp;}
    lb.addEventListener("change",function(){history.replaceState(null,"",lb.value?"?birim="+encodeURIComponent(lb.value):location.pathname);suzUygula();});if(lb.value)suzUygula();}
  if(suz)suz.addEventListener("input",suzUygula);
  if(mg0){try{if(localStorage.getItem("csm-mulga")==="0")mg0.checked=false;}catch(x){}
    mg0.addEventListener("change",function(){try{localStorage.setItem("csm-mulga",mg0.checked?"1":"0");}catch(x){}suzUygula();});suzUygula();}

  // Liste sıralama: ada göre ya da tarihe göre (tarihi olmayanlar her zaman sonda)
  function karsilastir(tur){var son=tur.indexOf("son-")===0,yon=son?tur.slice(4):tur;return function(a,b){
    if(tur==="ad")return a.ad.localeCompare(b.ad,"tr");
    if(son){a={ad:a.ad,t:a.s||""};b={ad:b.ad,t:b.s||""};}
    if(!a.t!==!b.t)return a.t?-1:1;
    var f=yon==="yeni"?b.t.localeCompare(a.t):a.t.localeCompare(b.t);
    return f||a.ad.localeCompare(b.ad,"tr");};}
  var sir=document.getElementById("liste-sirala");
  if(sir){
    var tbody=document.querySelector("table.liste tbody");
    var uygula=function(){var tur=sir.value;try{localStorage.setItem("csm-sirala",tur);}catch(x){}
      Array.prototype.map.call(tbody.rows,function(r){return {r:r,ad:r.getAttribute("data-ad")||"",t:r.getAttribute("data-tarih")||"",s:r.getAttribute("data-son")||""};})
        .sort(karsilastir(tur)).forEach(function(x){tbody.appendChild(x.r);});
      document.querySelectorAll("table.liste th[data-sirala]").forEach(function(th){var k=th.getAttribute("data-sirala"),on=k==="son"?"son-":"";th.setAttribute("aria-sort",k==="ad"?(tur==="ad"?"ascending":"none"):(tur===on+"yeni"?"descending":tur===on+"eski"?"ascending":"none"));});};
    var ths=document.querySelectorAll("table.liste thead th");
    var sonTh=-1;Array.prototype.forEach.call(ths,function(th,i){if(th.getAttribute("data-kolon")==="son")sonTh=i;});
    [[0,"ad"],[2,"tarih"],[sonTh,"son"]].forEach(function(x){var th=ths[x[0]];if(!th)return;th.setAttribute("data-sirala",x[1]);th.setAttribute("tabindex","0");th.title="Sıralamak için tıklayın";
      var tik=function(){sir.value=x[1]==="ad"?"ad":x[1]==="son"?(sir.value==="son-yeni"?"son-eski":"son-yeni"):(sir.value==="yeni"?"eski":"yeni");uygula();};
      th.addEventListener("click",tik);th.addEventListener("keydown",function(ev){if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();tik();}});});
    var kayitli=null;try{kayitli=localStorage.getItem("csm-sirala");}catch(x){}
    if(kayitli&&/^(ad|yeni|eski|son-yeni|son-eski)$/.test(kayitli)&&sir.querySelector('option[value="'+kayitli+'"]'))sir.value=kayitli;
    uygula();
    sir.addEventListener("change",uygula);
  }

  var mAra=document.getElementById("metinde-ara");
  if(mAra){
    var metin=document.getElementById("metin"), asil=metin.innerHTML, zaman;
    mAra.addEventListener("input",function(){clearTimeout(zaman);zaman=setTimeout(function(){
      metin.innerHTML=asil; if(window.csmZaman)window.csmZaman(); var q=mAra.value.trim(); var bilgi=document.getElementById("metinde-sonuc");
      if(q.length<2){bilgi.textContent="";return;}
      var re=new RegExp(kacis(q),"gi"), say=0;
      var w=document.createTreeWalker(metin,NodeFilter.SHOW_TEXT), dugumler=[];
      while(w.nextNode())dugumler.push(w.currentNode);
      dugumler.forEach(function(d){ re.lastIndex=0; if(!re.test(d.nodeValue))return; re.lastIndex=0;
        var span=document.createElement("span"); span.innerHTML=e(d.nodeValue).replace(re,function(x){say++;return "<mark>"+x+"</mark>";});
        d.parentNode.replaceChild(span,d);});
      bilgi.textContent=say+" eşleşme"; var ilk=metin.querySelector("mark"); if(ilk)ilk.scrollIntoView({block:"center"});
    },250);});
  }

  // Tarihe göre görüntüleme: seçilen tarihten sonra eklenen/değişen/kaldırılan hükümler işaretlenir
  var zv=document.getElementById("zaman-veri"), zm=document.getElementById("metin");
  if(zv&&zm){(function(){
    var V; try{V=JSON.parse(zv.textContent);}catch(x){return;}
    var kay=document.getElementById("zaman-kaydir"), ti=document.getElementById("zaman-tarih"), durum=document.getElementById("zaman-durum"),
        cizgi=document.getElementById("zaman-cizgi"), yal=document.getElementById("zaman-yalniz"), pan=document.getElementById("zaman"), secili="";
    var bugun=new Date().toISOString().slice(0,10), tum=V.n.concat([bugun]);
    var ms=function(t){return Date.parse((t+"-01-01").slice(0,10));};
    kay.min=0; kay.max=tum.length-1; kay.step=1; kay.value=tum.length-1;
    var t0=ms(tum[0]), t1=ms(bugun), dugmeler=[];
    tum.forEach(function(t,i){var d=document.createElement("button");d.type="button";d.className="zn-nokta"+(i===tum.length-1?" son":"");
      d.style.left=(t1>t0?(ms(t)-t0)/(t1-t0)*100:0)+"%";d.title=i===tum.length-1?"Güncel metin":tr(t);d.tabIndex=-1;
      d.addEventListener("click",function(){sec(i===tum.length-1?"":t);});cizgi.appendChild(d);dugmeler.push(d);});
    var u0=document.createElement("span");u0.className="zn-uc";u0.textContent=tr(tum[0]);cizgi.appendChild(u0);
    var u1=document.createElement("span");u1.className="zn-uc sag";u1.textContent="Bugün";cizgi.appendChild(u1);
    // RG değişiklik metinlerinden kurulmuş tarihli sürümler
    var surumler=null, surumSoz=null, asilHtml=zm.innerHTML, gsec=document.getElementById("zaman-goster");
    function surumYukle(){if(!V.v)return Promise.resolve(null);if(surumSoz)return surumSoz;
      var ad=location.pathname.split("/").pop().replace(/\.html$/,"");
      surumSoz=fetch("../../surum/"+ad+".json").then(function(r){if(!r.ok)throw 0;return r.json();}).then(function(x){surumler=x;return x;}).catch(function(){surumSoz=null;return null;});return surumSoz;}
    function surumGoster(D){var v=null;(surumler||[]).forEach(function(x){if(x.t<=D)v=x;});if(!v)return false;
      zm.innerHTML=v.h;var i=surumler.indexOf(v),son=i===surumler.length-1;
      var kay=surumler.slice(0,i+1).map(function(x){return (x.url?'<a href="'+e(x.url)+'" target="_blank" rel="noopener">':"")+tr(x.t)+(x.ilk?" (ilk yayım)":"")+(x.url?"</a>":" (metni bulunamadı)");}).join(", ");
      durum.innerHTML="<p><strong>"+tr(D)+" tarihindeki metin gösteriliyor.</strong> "+(v.ilk?"Bu, Resmî Gazete'de ilk yayımlanan metindir.":"İlk yayım metnine "+tr(v.t)+" tarihine kadarki değişiklikler Resmî Gazete'deki değişiklik metinlerinden işlenerek oluşturulmuştur.")
        +(v.belirsiz?" "+v.belirsiz+" maddenin metni kesinleştirilemedi; bu maddeler işaretlidir.":"")
        +(surumler.slice(0,i+1).some(function(x){return x.eksik;})?" Bazı değişiklik metinleri bulunamadığı için ilgili maddeler eksik kalmış olabilir.":"")
        +(son?"":" Bu tarihten sonra "+(surumler.length-1-i)+" değişiklik daha yapılmıştır.")
        +"</p><p class=\"zaman-kaynak\">Kaynak Resmî Gazete sayıları: "+kay+"</p>";
      return true;}
    function sinif(o){var k=o[1],s=(o[2]||"").toLocaleLowerCase("tr"),bas=o[3]>0&&!/ibare|cümle|kelime|başlık|tanım/.test(s);
      if(k==="e")return bas?"yok":"farkli";
      if(k==="m"||k==="i")return bas?"kalkti":"farkli";
      return "farkli";}
    var METIN={yok:"Seçilen tarihte bu hüküm yoktu; {t} tarihinde eklendi.",farkli:"Seçilen tarihte bu hükmün metni farklıydı; {t} tarihinde değiştirildi.",kalkti:"Seçilen tarihte bu hüküm yürürlükteydi; {t} tarihinde {f}."};
    function etiket(cls,ev,o){var m=METIN[cls].replace("{t}",tr(o[0])).replace("{f}",o[1]==="i"?"iptal edildi":"yürürlükten kaldırıldı");
      var ayr=ev.map(function(x){return x[4];}).filter(function(x,i,a){return x&&a.indexOf(x)===i;}).slice(0,4);
      var eski=ayr.some(function(x){return /ibaresi|önceki metin/i.test(x);});
      if(cls!=="yok")m+=eski?" Değişikliğin ayrıntısı aşağıda.":" Seçilen tarihteki metni sitede bulunmuyor.";
      var diger=ev.filter(function(x){return x[0]!==o[0];}).map(function(x){return tr(x[0]);}).filter(function(x,i,a){return a.indexOf(x)===i;});
      if(diger.length)m+=" Bu hükümde ayrıca "+diger.join(", ")+" tarihli değişiklik var.";
      var d=document.createElement("div");d.className="zn "+cls;d.innerHTML="<strong>"+e(m)+"</strong>"+ayr.map(function(x){return "<br><small>"+e(x)+"</small>";}).join("");return d;}
    function temizle(){zm.querySelectorAll(".zn").forEach(function(x){x.remove();});
      zm.querySelectorAll(".z-yok,.z-farkli,.z-kalkti,.z-gizli").forEach(function(x){x.classList.remove("z-yok","z-farkli","z-kalkti","z-gizli");});}
    function uygula(){if(zm.querySelector(".zn.belirsiz")||zm.getAttribute("data-surum")){zm.innerHTML=asilHtml;zm.removeAttribute("data-surum");}temizle();var D=secili;
      dugmeler.forEach(function(d,i){d.classList.toggle("aktif",D?(tum[i]<=D&&(i===tum.length-1||tum[i+1]>D)):i===tum.length-1);});
      if(!D){durum.innerHTML="";return;}
      if(V.v&&(!gsec||gsec.checked)&&(!V.b||D>=V.b)&&!(V.s&&V.s.t&&D>=V.s.t)){
        if(surumler){if(surumGoster(D)){zm.setAttribute("data-surum","1");return;}}
        else{durum.innerHTML="<p>Bu tarihteki metin yükleniyor…</p>";surumYukle().then(function(){if(secili===D)uygula();});return;}}
      var h="<p><strong>"+tr(D)+" tarihindeki durum.</strong> ";
      if(V.b&&D<V.b){var o=(V.o||[]).filter(function(x){return !x.b||x.b<=D;});
        durum.innerHTML=h+"Bu "+e(V.tur).toLocaleLowerCase("tr")+" o tarihte henüz yürürlükte değildi (tarihi: "+tr(V.b)+")."+(o.length?" O tarihte yürürlükte olan önceki düzenleme: "+o.map(function(x){return '<a href="'+e(x.u)+'?tarih='+D+'">'+e(x.a)+"</a>";}).join(", ")+".":" Önceki düzenlemenin metni sitede bulunmuyor.")+"</p>";return;}
      if(V.s&&V.s.t&&D>=V.s.t){durum.innerHTML=h+"Bu düzenleme o tarihte yürürlükten kalkmıştı ("+tr(V.s.t)+"). Yerine geçen ya da kaldıran düzenleme: <a href=\""+e(V.s.u)+"?tarih="+D+"\">"+e(V.s.a)+"</a>.</p>";return;}
      var say={yok:0,farkli:0,kalkti:0}, ilk=null, isaretli=new Set();
      var els=Array.prototype.slice.call(zm.querySelectorAll("[data-z]"));
      els.forEach(function(el){var ev;try{ev=JSON.parse(el.getAttribute("data-z"));}catch(x){return;}
        ev=ev.filter(function(o){return o[0]>D;}).sort(function(a,b){return a[0]<b[0]?-1:1;});
        if(!ev.length||isaretli.has(el))return;
        var tumu=ev.filter(function(o){return o[3]===1;}), karar=tumu.length?tumu[0]:ev[0], cls=sinif(karar);
        var grup=[el];
        if(tumu.length&&el.classList.contains("madde")){var n=el.nextElementSibling;while(n&&!n.classList.contains("madde")&&!/^H[1-4]$/.test(n.tagName)){grup.push(n);n=n.nextElementSibling;}}
        grup.forEach(function(g){g.classList.add("z-"+cls);isaretli.add(g);});
        el.parentNode.insertBefore(etiket(cls,ev,karar),el);say[cls]++;if(!ilk)ilk=el;});
      var parca=[];if(say.yok)parca.push(say.yok+" hüküm o tarihte yoktu");if(say.farkli)parca.push(say.farkli+" hükmün metni farklıydı");if(say.kalkti)parca.push(say.kalkti+" hüküm sonradan kaldırıldı");
      h+=parca.length?"Bu tarihten sonraki değişiklikler işaretlendi: "+parca.join(", ")+". ":((V.l||[]).some(function(x){return x[0]>D;})?"Bu tarihten sonra değişiklik yapılmış, ancak değişen yerler metinde işaretli değil; değişiklikler aşağıdaki listede. ":"Metinde bu tarihten sonraki bir değişiklik notu bulunmuyor. ");
      if(ilk)h+='<button type="button" class="zaman-ilk" id="zaman-ilk">İlk işarete git ↓</button>';
      h+="</p>";
      var l=(V.l||[]).filter(function(x){return x[0]>D;});
      if(l.length)h+="<details"+(parca.length?"":" open")+"><summary>Değişiklik listesine göre bu tarihten sonraki "+l.length+" değişiklik</summary><ul>"+l.map(function(x){return "<li>"+tr(x[0])+(x[1]?" — "+e(x[1]):"")+"</li>";}).join("")+"</ul></details>";
      durum.innerHTML=h;var ig=document.getElementById("zaman-ilk");if(ig)ig.addEventListener("click",function(){ilk.previousElementSibling.scrollIntoView({block:"center",behavior:"smooth"});});
      if(yal.checked)Array.prototype.forEach.call(zm.children,function(c){if(!isaretli.has(c)&&!c.classList.contains("zn")&&!/^H[1-3]$/.test(c.tagName))c.classList.add("z-gizli");});}
    function sec(D){if(D&&D>=bugun)D="";secili=D||"";ti.value=secili;
      var i=tum.length-1;if(secili){i=0;tum.forEach(function(t,j){if(j<tum.length-1&&t<=secili)i=j;});}kay.value=i;
      try{var q=new URLSearchParams(location.search);if(secili)q.set("tarih",secili);else q.delete("tarih");history.replaceState(null,"",location.pathname+(q.toString()?"?"+q:"")+location.hash);}catch(x){}
      uygula();}
    kay.addEventListener("input",function(){var i=+kay.value;sec(i===tum.length-1?"":tum[i]);});
    ti.addEventListener("change",function(){sec(ti.value);});
    document.getElementById("zaman-guncel").addEventListener("click",function(){sec("");});
    yal.addEventListener("change",uygula);if(gsec)gsec.addEventListener("change",uygula);
    window.csmZaman=uygula;
    var ilkT=new URLSearchParams(location.search).get("tarih");
    if(ilkT&&/^\d{4}-\d{2}-\d{2}$/.test(ilkT)){pan.open=true;sec(ilkT);}
  })();}

  // Sayfa başına dön düğmesi
  var yk=document.getElementById("yukari");
  if(yk){var ykGor=function(){yk.hidden=window.scrollY<600;};window.addEventListener("scroll",ykGor,{passive:true});ykGor();
    yk.addEventListener("click",function(){window.scrollTo({top:0,behavior:"smooth"});});}

  // Yazı boyutu (tercih tarayıcıda saklanır)
  var yb=document.getElementById("yazi-buyut"), yc=document.getElementById("yazi-kucult"), mt=document.getElementById("metin");
  if(yb&&yc&&mt){var olcek=1;try{olcek=parseFloat(localStorage.getItem("csm-yazi"))||1;}catch(x){}
    var olcekUygula=function(){olcek=Math.round(Math.min(1.6,Math.max(0.8,olcek))*10)/10;mt.style.setProperty("--yazi-olcek",olcek);try{localStorage.setItem("csm-yazi",olcek);}catch(x){}};
    olcekUygula();yb.addEventListener("click",function(){olcek+=0.1;olcekUygula();});yc.addEventListener("click",function(){olcek-=0.1;olcekUygula();});}

  // Madde numarasına git
  var mg=document.getElementById("madde-git");
  if(mg){var git=function(){var h=document.getElementById("madde-"+parseInt(mg.value,10));
      if(!h){mg.setCustomValidity("Bu numarada madde bulunamadı");mg.reportValidity();return;}
      mg.setCustomValidity("");h.scrollIntoView({block:"start",behavior:"smooth"});h.classList.add("madde-vurgu");setTimeout(function(){h.classList.remove("madde-vurgu");},1800);};
    mg.addEventListener("change",git);mg.addEventListener("input",function(){mg.setCustomValidity("");});
    mg.addEventListener("keydown",function(ev){if(ev.key==="Enter"){ev.preventDefault();git();}});}

  var form=document.getElementById("arama-formu");
  if(!form)return;
  var dizin=null, metinler={}, parcaSay=null, yuklenen=0, metinSoz=null, metinHata=false, calismaNo=0, aktifGoster=null;
  var p=new URLSearchParams(location.search); var qEl=document.getElementById("q"); qEl.value=p.get("q")||"";
  if(p.get("kapsam")==="metin")form.querySelector("input[value=metin]").checked=true;
  var birimEl=document.getElementById("birim-ara"), birimIlk=p.get("birim")||"";
  function birimDoldur(){if(!birimEl||birimEl.options.length>1||!dizin)return;var say={};dizin.forEach(function(b){(b.u||[]).forEach(function(u){say[u]=(say[u]||0)+1;});});
    var ad=Object.keys(say).sort(function(a,b){return a.localeCompare(b,"tr");}),daire=function(u){return /Dairesi Başkanlığı$/.test(u);};
    [["Genel müdürlükler ve başkanlıklar",ad.filter(function(u){return !daire(u);})],["Daire başkanlıkları",ad.filter(daire)]].forEach(function(g){var og=document.createElement("optgroup");og.label=g[0];
      g[1].forEach(function(u){var o=document.createElement("option");o.value=u;o.textContent=u+" ("+say[u]+")";og.appendChild(o);});birimEl.appendChild(og);});
    if(birimIlk){birimEl.value=birimIlk;birimIlk="";}}
  function yukle(ad){return fetch(kok+"assets/"+ad).then(function(r){if(!r.ok)throw new Error(r.status);return r.json();});}
  // Tam metinler parça parça indirilir; her parça gelince sonuçlar güncellenir. Sadeleştirilmiş metin bellekte tutulur.
  function metinleriYukle(){
    var ilerle=function(){if(aktifGoster)aktifGoster();};
    if(metinSoz)return metinSoz;
    metinHata=false; yuklenen=0;
    metinSoz=yukle("metin/parca.json?t="+Date.now()).then(function(pm){parcaSay=pm.n;
      var sira=Promise.resolve(), i;
      var al=function(n){return yukle("metin/"+n+".json?v="+pm.s).then(function(m){m.forEach(function(x){metinler[x.i]={x:x.x,s:sade(x.x)};});yuklenen++;ilerle();});};
      var esz=[];for(i=0;i<pm.n;i++)esz.push(al(i));
      return Promise.all(esz);
    }).catch(function(){metinHata=true;metinSoz=null;ilerle();});
    return metinSoz;
  }
  function calistir(){
    var benim=++calismaNo;
    var q=sade(qEl.value), kapsam=form.querySelector("input[name=kapsam]:checked").value;
    var sayi=document.getElementById("sayi").value.trim(), y1=+document.getElementById("yil1").value||0, y2=+document.getElementById("yil2").value||9999;
    var turler={}; form.querySelectorAll("input[name=tur]:checked").forEach(function(c){turler[c.value]=1;});
    var metinAra = kapsam==="metin" && q;
    document.getElementById("sonuc-bilgi").textContent="Aranıyor…";
    var goster=aktifGoster=function(){
      if(benim!==calismaNo||!dizin)return;
      var kelimeler=q?q.split(" "):[], sonuc=[];
      dizin.forEach(function(b){
        if(!turler[b.t==="khk"?"kanun":b.t==="ck"?"bkk":b.t])return;
        var yil=+((b.r||b.d||"").slice(0,4))||0; if((y1>0||y2<9999)&&(yil<y1||yil>y2))return;
        if(sayi&&String(b.s).indexOf(sayi)<0&&String(b.rs).indexOf(sayi)<0)return;
        var ma=document.getElementById("mulga-ara");if(ma&&!ma.checked&&b.x)return;
        if(birimEl&&birimEl.value&&(b.u||[]).indexOf(birimEl.value)<0)return;
        var parca="";
        if(kelimeler.length){
          var hedef=sade(b.b+" "+b.k+" "+(b.e||[]).join(" ")+" "+b.s);
          var tamam=kelimeler.every(function(k){return hedef.indexOf(k)>=0;});
          if(!tamam&&metinAra&&metinler[b.i]){var sm=metinler[b.i].s;tamam=kelimeler.every(function(k){return sm.indexOf(k)>=0;});
            if(tamam){var ham=metinler[b.i].x,ilk=qEl.value.trim().split(/\s+/)[0],ix=ham.toLocaleLowerCase("tr").indexOf(ilk.toLocaleLowerCase("tr"));if(ix<0)ix=0;parca=ham.slice(Math.max(0,ix-120),ix+220);}}
          if(!tamam)return;
        }
        sonuc.push({b:b,p:parca});
      });
      var ssir=document.getElementById("sonuc-sirala"), stur=ssir?ssir.value:"yeni";
      var kars=karsilastir(stur);
      sonuc.sort(function(a,b){return kars({ad:sade(a.b.b),t:a.b.d||a.b.r||""},{ad:sade(b.b.b),t:b.b.d||b.b.r||""});});
      var durum="";
      if(metinAra){ if(metinHata)durum=" — tam metinler indirilemedi, yalnız başlık ve künyede arandı. Sayfayı yenileyip tekrar deneyin.";
        else if(parcaSay===null||yuklenen<parcaSay)durum=" — tam metinler taranıyor"+(parcaSay?" ("+yuklenen+"/"+parcaSay+")":"")+"…"; }
      document.getElementById("sonuc-bilgi").textContent=sonuc.length+" sonuç bulundu"+(sonuc.length>300?" (ilk 300 gösteriliyor)":"")+durum;
      var isaretle=function(s){var x=e(s);qEl.value.trim().split(/\s+/).filter(function(k){return k.length>1;}).forEach(function(k){x=x.replace(new RegExp("("+kacis(e(k))+")","gi"),"<mark>$1</mark>");});return x;};
      document.getElementById("sonuclar").innerHTML=sonuc.slice(0,300).map(function(s){var b=s.b;
        var ust=[TUR[b.t],b.d&&("Tarih: "+tr(b.d)),b.s&&("Sayı: "+b.s),b.r&&("RG: "+tr(b.r)+(b.rs?" / "+b.rs:"")),b.m?"Tam metin":"Künye",b.x?"Mülga":""].filter(Boolean).join(" · ");
        return '<div class="sonuc"><a href="'+kok+'mevzuat/'+b.t+'/'+b.i+'.html">'+isaretle(b.b)+'</a><div class="ust-bilgi">'+e(ust)+'</div>'+(s.p?'<div class="parca">…'+isaretle(s.p)+'…</div>':(b.k?'<div class="parca">'+e(b.k)+'</div>':''))+'</div>';}).join("");
    };
    (dizin?Promise.resolve():yukle("dizin.json?t="+Date.now()).then(function(d){dizin=d;})).then(function(){
      birimDoldur();
      goster();
      if(metinAra&&(parcaSay===null||yuklenen<parcaSay))metinleriYukle();
    }).catch(function(){if(benim===calismaNo)document.getElementById("sonuc-bilgi").textContent="Arama dizini yüklenemedi. Sayfayı yenileyip tekrar deneyin.";});
  }
  form.addEventListener("submit",function(ev){ev.preventDefault();history.replaceState(null,"","?q="+encodeURIComponent(qEl.value)+(birimEl&&birimEl.value?"&birim="+encodeURIComponent(birimEl.value):""));calistir();});
  if(birimEl)birimEl.addEventListener("change",function(){history.replaceState(null,"","?q="+encodeURIComponent(qEl.value)+(birimEl.value?"&birim="+encodeURIComponent(birimEl.value):""));calistir();});
  var ssir2=document.getElementById("sonuc-sirala"); if(ssir2)ssir2.addEventListener("change",calistir);
  var ma2=document.getElementById("mulga-ara"); if(ma2)ma2.addEventListener("change",calistir);
  calistir();
})();

