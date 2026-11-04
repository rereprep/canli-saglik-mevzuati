(function(){
  "use strict";
  var kok = (document.querySelector('link[rel=stylesheet]').getAttribute('href')||'').replace('assets/stil.css','');
  var TUR = {kanun:"Kanun",cbk:"Cumhurbaşkanlığı Kararnamesi",khk:"Kanun Hükmünde Kararname",tuzuk:"Tüzük",yonetmelik:"Yönetmelik",yonerge:"Yönerge",genelge:"Genelge",teblig:"Tebliğ",protokol:"Protokol",yazi:"Resmî Yazı"};
  var HARF = {"ç":"c","ğ":"g","ı":"i","ö":"o","ş":"s","ü":"u","â":"a","î":"i","û":"u"};
  function sade(s){return (s||"").toLocaleLowerCase("tr").replace(/[çğıöşüâîû]/g,function(c){return HARF[c];}).normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^0-9a-z]+/g," ").trim();}
  function e(s){return String(s||"").replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function kacis(s){return s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");}
  function tr(iso){var m=/(\d{4})-(\d{2})-(\d{2})/.exec(iso||"");return m?m[3]+"."+m[2]+"."+m[1]:(iso||"");}

  var suz=document.getElementById("liste-suz");
  if(suz){suz.addEventListener("input",function(){var q=sade(suz.value);document.querySelectorAll("table.liste tbody tr").forEach(function(tr){tr.style.display=!q||sade(tr.textContent).indexOf(q)>=0?"":"none";});});}

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

  var form=document.getElementById("arama-formu");
  if(!form)return;
  var dizin=null, metinler=null;
  var p=new URLSearchParams(location.search); var qEl=document.getElementById("q"); qEl.value=p.get("q")||"";
  if(p.get("kapsam")==="metin")form.querySelector("input[value=metin]").checked=true;
  function yukle(ad){return fetch(kok+"assets/"+ad).then(function(r){return r.json();});}
  function calistir(){
    var q=sade(qEl.value), kapsam=form.querySelector("input[name=kapsam]:checked").value;
    var sayi=document.getElementById("sayi").value.trim(), y1=+document.getElementById("yil1").value||0, y2=+document.getElementById("yil2").value||9999;
    var turler={}; form.querySelectorAll("input[name=tur]:checked").forEach(function(c){turler[c.value]=1;});
    var gerek = kapsam==="metin" && q && !metinler ? yukle("metinler.json").then(function(m){metinler={};m.forEach(function(x){metinler[x.i]=x.x;});}) : Promise.resolve();
    document.getElementById("sonuc-bilgi").textContent="Aranıyor…";
    Promise.all([dizin?null:yukle("dizin.json").then(function(d){dizin=d;}),gerek]).then(function(){
      var kelimeler=q?q.split(" "):[], sonuc=[];
      dizin.forEach(function(b){
        if(!turler[b.t])return;
        var yil=+((b.r||b.d||"").slice(0,4))||0; if((y1>0||y2<9999)&&(yil<y1||yil>y2))return;
        if(sayi&&String(b.s).indexOf(sayi)<0&&String(b.rs).indexOf(sayi)<0)return;
        var parca="";
        if(kelimeler.length){
          var hedef=sade(b.b+" "+b.k+" "+(b.e||[]).join(" ")+" "+b.s);
          var tamam=kelimeler.every(function(k){return hedef.indexOf(k)>=0;});
          if(!tamam&&kapsam==="metin"&&metinler&&metinler[b.i]){var sm=sade(metinler[b.i]);tamam=kelimeler.every(function(k){return sm.indexOf(k)>=0;});
            if(tamam){var ham=metinler[b.i],ilk=qEl.value.trim().split(/\s+/)[0],ix=ham.toLocaleLowerCase("tr").indexOf(ilk.toLocaleLowerCase("tr"));if(ix<0)ix=0;parca=ham.slice(Math.max(0,ix-120),ix+220);}}
          if(!tamam)return;
        }
        sonuc.push({b:b,p:parca});
      });
      sonuc.sort(function(a,b){return (b.b.r||b.b.d||"").localeCompare(a.b.r||a.b.d||"");});
      document.getElementById("sonuc-bilgi").textContent=sonuc.length+" sonuç bulundu"+(sonuc.length>300?" (ilk 300 gösteriliyor)":"");
      var isaretle=function(s){var x=e(s);qEl.value.trim().split(/\s+/).filter(function(k){return k.length>1;}).forEach(function(k){x=x.replace(new RegExp("("+kacis(e(k))+")","gi"),"<mark>$1</mark>");});return x;};
      document.getElementById("sonuclar").innerHTML=sonuc.slice(0,300).map(function(s){var b=s.b;
        var ust=[TUR[b.t],b.d&&("Tarih: "+tr(b.d)),b.s&&("Sayı: "+b.s),b.r&&("RG: "+tr(b.r)+(b.rs?" / "+b.rs:"")),b.m?"Tam metin":"Künye"].filter(Boolean).join(" · ");
        return '<div class="sonuc"><a href="'+kok+'mevzuat/'+b.t+'/'+b.i+'.html">'+isaretle(b.b)+'</a><div class="ust-bilgi">'+e(ust)+'</div>'+(s.p?'<div class="parca">…'+isaretle(s.p)+'…</div>':(b.k?'<div class="parca">'+e(b.k)+'</div>':''))+'</div>';}).join("");
    });
  }
  form.addEventListener("submit",function(ev){ev.preventDefault();history.replaceState(null,"","?q="+encodeURIComponent(qEl.value));calistir();});
  calistir();
})();

