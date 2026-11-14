
"""Uydurma/yanlış metin denetimi: belge metni ile kaynak sayfaların makine okuması hizalanır.
Kullanım: python denetle.py q4   (calisma/q4/doc.json: {md_yolu: [ilk_pdf_sayfa, son_pdf_sayfa]}, calisma/q4/j/pNNNN.json)"""
import json,re,os,difflib,sys,glob,statistics
K=sys.argv[1]; D='/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/calisma/'+K
ids={k['i'] for k in json.load(open('_site/assets/dizin.json',encoding='utf-8'))}
def W(s): return [x for x in re.findall(r'[0-9A-Za-zçğıöşüÇĞİÖŞÜâîû]+',s) if len(x)>1]
tr=str.maketrans('çğıöşüâîûİ','cgiosuaiui')
def fold(w): return w.replace('I','i').lower().translate(tr)
def k(w): return fold(w)[:4]
def join(js):
    t=''
    for jf in js:
        if not os.path.exists(jf): continue
        for l in json.load(open(jf,encoding='utf-8'))['lines']:
            x=l['text'].strip(); t=(t[:-1]+x) if t.endswith('-') else (t+' '+x)
    return t
doc=json.load(open(D+'/doc.json'))
out=[]
for f,(a,b) in doc.items():
    if not os.path.exists(f): continue
    A=W(open(f,encoding='utf-8').read().split('---',2)[2])[:6000]; B=W(join([D+'/j/p%04d.json'%q for q in range(a,b+2)]))[:9000]
    if len(A)<40: continue
    ka=[k(x) for x in A]; kb=[k(x) for x in B]
    sm=difflib.SequenceMatcher(None,ka,kb,autojunk=False)
    m=sum(x.size for x in sm.get_matching_blocks()); vb=set(kb)
    deg=[];uyd=[]
    for tg,i1,i2,j1,j2 in sm.get_opcodes():
        if tg=='equal': continue
        sa=A[i1:i2]; sb=B[j1:j2]
        if len(sa)>=4 and sum(1 for x in sa if x[0].islower())/len(sa)>=0.6:
            if tg=='replace' and len(sb)>=4 and sum(1 for x in sb if x[0].islower())/len(sb)>=0.6 and abs(len(sa)-len(sb))<=max(6,len(sa)):
                r=difflib.SequenceMatcher(None,fold(' '.join(sa)),fold(' '.join(sb))).ratio()
                if r<0.55: deg.append((' '.join(sa)[:200],' '.join(sb)[:200]))
            elif len(sa)>=8:
                inv=sum(1 for x in ka[i1:i2] if x in vb)/len(sa)
                if inv<0.8: uyd.append((round(inv,2),' '.join(sa)[:260]))
    out.append({'f':f,'puan':round(m/len(A),2),'ters':round(m/max(1,len(B)),2),'n':len(A),'nk':len(B),'gorunen':os.path.basename(f)[:-3] in ids,'deg':deg,'uyd':uyd})
out.sort(key=lambda r:r['puan'])
json.dump(out,open(D+'/denetim_sonuc.json','w'),ensure_ascii=False)
print(len(out),'medyan',statistics.median(r['puan'] for r in out))
for r in out:
    if not r['gorunen']: continue
    if r['puan']<0.8 or r['deg'] or r['uyd']:
        print('##',r['puan'],r['ters'],r['n'],r['nk'],r['f'].split('/',1)[1][:72])
        for a,b in r['deg'][:3]: print('   M:',a[:150]); print('   K:',b[:150])
        for i,a in r['uyd'][:2]: print('   U',i,a[:200])

