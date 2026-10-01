"""국립해양조사원(KHOA) 바다누리 Open API 에서 경기만 조류예보(시계열)와 인천 조석예보를 받아
data/khoa_currents.json 으로 저장한다.

사용법:
  python fetch_khoa.py --key <ServiceKey> [--start 20260101] [--days 2] [--list-only]

- 지점 목록은 ObsServiceObj API 로 받아 경기만 범위(위도 37.10~37.92, 경도 125.95~126.95) 안의
  조류예보 지점만 고른다. --list-only 로 지점 목록만 확인할 수 있다.
- 조류예보(시계열)은 fcTidalCurrent API(ObsCode, Date=YYYYMMDD)를 하루 단위로 호출한다.
- 조석예보(고저조)는 tideObsPreTab API(인천 DT_0001)를 같은 날짜 범위로 호출한다. 실패해도 조류 자료만으로 저장한다.
- API 응답 필드명이 문서 개정으로 바뀔 수 있어 여러 후보 이름을 받아들이고, 못 읽은 응답은 data/raw/ 에 남긴다.
"""
import argparse, datetime as dt, json, os, sys, time, urllib.parse, urllib.request

BASE='http://www.khoa.go.kr/api/oceangrid/{svc}/search.do'
BBOX=dict(lat0=37.10,lat1=37.92,lon0=125.95,lon1=126.95)
TIDE_STATION=('DT_0001','인천')
here=os.path.dirname(os.path.abspath(__file__))
RAW=os.path.join(here,'data','raw'); os.makedirs(RAW,exist_ok=True)

def call(svc,key,**params):
    q=dict(ServiceKey=key,ResultType='json',**params)
    url=BASE.format(svc=svc)+'?'+urllib.parse.urlencode(q)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url,timeout=30) as r: txt=r.read().decode('utf-8','replace')
            break
        except Exception as e:
            if attempt==3: raise
            time.sleep(2**attempt)
    tag=svc+'_'+'_'.join(str(v) for k,v in params.items())
    open(os.path.join(RAW,tag+'.json'),'w',encoding='utf-8').write(txt)
    try: js=json.loads(txt)
    except json.JSONDecodeError:
        raise RuntimeError(f'{svc}: JSON 이 아닌 응답 (키 또는 파라미터 확인): {txt[:200]}')
    res=js.get('result',js)
    err=res.get('error') if isinstance(res,dict) else None
    if err: raise RuntimeError(f'{svc}: API 오류 {err}')
    data=res.get('data') if isinstance(res,dict) else None
    if data is None: raise RuntimeError(f'{svc}: data 없음: {txt[:200]}')
    return data if isinstance(data,list) else [data]

def pick(row,*names,default=None):
    for n in names:
        if n in row and row[n] not in ('',None): return row[n]
    return default

def list_stations(key):
    rows=call('ObsServiceObj',key)
    out=[]
    for r in rows:
        try: lat=float(pick(r,'obs_lat','lat')); lon=float(pick(r,'obs_lon','lon'))
        except (TypeError,ValueError): continue
        out.append(dict(id=pick(r,'obs_post_id','obs_code','id'),name=pick(r,'obs_post_name','name'),lat=lat,lon=lon,
                        type=pick(r,'data_type','obs_object','type',default='')))
    return out

def in_bbox(s): return BBOX['lat0']<=s['lat']<=BBOX['lat1'] and BBOX['lon0']<=s['lon']<=BBOX['lon1']

def parse_time(v):
    v=str(v).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M','%Y%m%d%H%M','%Y-%m-%dT%H:%M:%S'):
        try: return dt.datetime.strptime(v,fmt).strftime('%Y-%m-%dT%H:%M:%S+09:00')
        except ValueError: pass
    return None

def fetch_current(key,st,dates):
    series=[]
    for d in dates:
        rows=call('fcTidalCurrent',key,ObsCode=st['id'],Date=d)
        for r in rows:
            t=parse_time(pick(r,'pred_time','record_time','time','date_time',default=''))
            sp=pick(r,'current_speed','cur_speed','speed','current_sp'); di=pick(r,'current_dir','cur_dir','dir','current_direct')
            if t is None or sp is None or di is None: continue
            try: series.append([t,float(sp),float(di)])      # 유속 cm/s, 유향 deg(흘러가는 방향)
            except ValueError: continue
    return series

def fetch_tide(key,dates):
    series=[]
    for d in dates:
        rows=call('tideObsPreTab',key,ObsCode=TIDE_STATION[0],Date=d)
        for r in rows:
            t=parse_time(pick(r,'tide_time','record_time','pred_time','time',default=''))
            lv=pick(r,'tide_level','level','tide_hl_level')
            if t is None or lv is None: continue
            try: series.append([t,float(lv)])               # cm, 기본수준면 기준
            except ValueError: continue
    if series:
        mean=sum(v for _,v in series)/len(series)
        series=[[t,v-mean] for t,v in series]               # 평균 기준으로 바꿈
    return series

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--key',required=True); ap.add_argument('--start',default=dt.date.today().strftime('%Y%m%d'))
    ap.add_argument('--days',type=int,default=2); ap.add_argument('--list-only',action='store_true'); a=ap.parse_args()
    stations=list_stations(a.key)
    cur=[s for s in stations if in_bbox(s) and ('조류' in str(s['type']))]
    if not cur: cur=[s for s in stations if in_bbox(s) and str(s['id']).upper().startswith(('17','16','TC','CU'))]
    print(f'전체 지점 {len(stations)}곳, 경기만 조류 지점 후보 {len(cur)}곳')
    for s in cur: print(f"  {s['id']:>10}  {s['name']:<14} {s['lat']:.4f} {s['lon']:.4f}  {s['type']}")
    if a.list_only: return
    d0=dt.datetime.strptime(a.start,'%Y%m%d').date(); dates=[(d0+dt.timedelta(days=i)).strftime('%Y%m%d') for i in range(a.days)]
    out=dict(fetched=dt.datetime.now().strftime('%Y-%m-%d %H:%M'),source='해양수산부 국립해양조사원 바다누리 해양정보 Open API',dates=dates,stations=[],tide=None)
    for s in cur:
        try: ser=fetch_current(a.key,s,dates)
        except Exception as e: print(f"  {s['name']}: 실패 {e}"); continue
        if ser: out['stations'].append(dict(id=s['id'],name=s['name'],lat=s['lat'],lon=s['lon'],series=ser)); print(f"  {s['name']}: {len(ser)}개")
        else: print(f"  {s['name']}: 자료 없음")
    tide_dates=[(d0+dt.timedelta(days=i)).strftime('%Y%m%d') for i in range(-1,a.days+1)]   # 보간을 위해 앞뒤 하루씩 더 받음
    try:
        ts=fetch_tide(a.key,tide_dates)
        if ts: out['tide']=dict(station=TIDE_STATION[0],name=TIDE_STATION[1],series=ts); print(f'조석예보 {len(ts)}개')
    except Exception as e: print('조석예보 실패:',e)
    p=os.path.join(here,'data','khoa_currents.json'); json.dump(out,open(p,'w',encoding='utf-8'),ensure_ascii=False)
    print('저장:',p,'지점',len(out['stations']),'곳. 이어서 python build_page.py 를 실행하세요.')
    if not out['stations']: sys.exit(1)

if __name__=='__main__': main()
