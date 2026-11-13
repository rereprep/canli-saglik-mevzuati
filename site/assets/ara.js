(function(){
  "use strict";
  var kok = (document.querySelector('link[rel=stylesheet]').getAttribute('href')||'').split('assets/stil.css')[0];
  var TUR = {kanun:"Kanun",cbk:"Cumhurbaşkanlığı Kararnamesi",khk:"Kanun Hükmünde Kararname",bkk:"Bakanlar Kurulu Kararı",tuzuk:"Tüzük",yonetmelik:"Yönetmelik",yonerge:"Yönerge",genelge:"Genelge",teblig:"Tebliğ",protokol:"Protokol",yazi:"Resmî Yazı"};
  var HARF = {"ç":"c","ğ":"g","ı":"i","ö":"o","ş":"s","ü":"u","â":"a","î":"i","û":"u"};
  function sade(s){return (s||"").toLocaleLowerCase("tr").replace(/[çğıöşüâîû]/g,function(c){return HARF[c];}).normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^0-9a-z]+/g," ").trim();}
  function e(s){return String(s||"").replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function kacis(s){return s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");}
  function tr(iso){var m=/(\d{4})-(\d{2})-(\d{2})/.exec(iso||"");return m?m[3]+"."+m[2]+"."+m[1]:(iso||"");}

  var suz=document.getElementById("liste-suz");
  var mg0=document.getElementById("mulga-goster");
  var suzUygula=function(){var q=suz?sade(suz.value):"",mul=!mg0||mg0.checked;document.querySelectorAll("table.liste tbody tr").forEach(function(tr){tr.style.display=((!q||sade(tr.textContent).indexOf(q)>=0)&&(mul||!tr.hasAttribute("data-mulga")))?"":"none";});};
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
      metin.innerHTML=asil; var q=mAra.value.trim(); var bilgi=document.getElementById("metinde-sonuc");
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
        if(!turler[b.t==="khk"?"kanun":b.t])return;
        var yil=+((b.r||b.d||"").slice(0,4))||0; if((y1>0||y2<9999)&&(yil<y1||yil>y2))return;
        if(sayi&&String(b.s).indexOf(sayi)<0&&String(b.rs).indexOf(sayi)<0)return;
        var ma=document.getElementById("mulga-ara");if(ma&&!ma.checked&&b.x)return;
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
      goster();
      if(metinAra&&(parcaSay===null||yuklenen<parcaSay))metinleriYukle();
    }).catch(function(){if(benim===calismaNo)document.getElementById("sonuc-bilgi").textContent="Arama dizini yüklenemedi. Sayfayı yenileyip tekrar deneyin.";});
  }
  form.addEventListener("submit",function(ev){ev.preventDefault();history.replaceState(null,"","?q="+encodeURIComponent(qEl.value));calistir();});
  var ssir2=document.getElementById("sonuc-sirala"); if(ssir2)ssir2.addEventListener("change",calistir);
  var ma2=document.getElementById("mulga-ara"); if(ma2)ma2.addEventListener("change",calistir);
  calistir();
})();

