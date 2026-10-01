"""template.html + assets/relief.jpg + assets/mask.json (+ data/khoa_currents.json) -> index.html
사용법: python build_page.py [--artifact out.html]
  index.html        : 브라우저에서 바로 여는 독립 실행 파일
  --artifact PATH   : <!doctype>/<html> 없이 본문만 쓴 사본(claude.ai 아티팩트 게시용)
"""
import base64, json, os, sys
here=os.path.dirname(os.path.abspath(__file__))
tpl=open(os.path.join(here,'template.html'),encoding='utf-8').read()
relief=base64.b64encode(open(os.path.join(here,'assets','relief.jpg'),'rb').read()).decode()
mask=open(os.path.join(here,'assets','mask.json'),encoding='utf-8').read().strip()
data_path=os.path.join(here,'data','khoa_currents.json')
khoa='null'
if os.path.exists(data_path):
    d=json.load(open(data_path,encoding='utf-8'))
    if d.get('stations'):
        khoa=json.dumps(d,ensure_ascii=False,separators=(',',':'))
        print(f"조류예보 지점 {len(d['stations'])}곳, 조석 {'있음' if d.get('tide') else '없음'} 내장")
    else:
        print('data/khoa_currents.json 에 지점 자료가 없어 개념 모형으로 빌드')
else:
    print('data/khoa_currents.json 없음: 개념 모형으로 빌드')
body=tpl.replace('__RELIEF__','data:image/jpeg;base64,'+relief).replace('__MASK__',mask).replace('__KHOA__',khoa)
out=os.path.join(here,'index.html')
open(out,'w',encoding='utf-8').write('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'+body+'\n</html>\n')
print('index.html', os.path.getsize(out),'bytes')
if '--artifact' in sys.argv:
    p=sys.argv[sys.argv.index('--artifact')+1]; open(p,'w',encoding='utf-8').write(body); print('artifact copy',p)
