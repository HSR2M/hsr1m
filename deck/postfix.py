"""pptxgenjs 산출물 후처리: 슬라이드마다 <p:cNvPr id> 를 고유하게 다시 매긴다.
pptxgenjs는 슬라이드 번호 자리표시자(id 25)와 표(id 16)에 고정 id를 쓰기 때문에
개체가 많은 슬라이드에서 id 가 중복되고, PowerPoint 는 이를 손상으로 보고 '복구'를 요구한다.
사용: python3 postfix.py 붕붕이_3DLabs_제안.pptx
"""
import re, sys, zipfile, shutil, os

def fix(path):
    tmp = path + ".tmp"
    fixed = 0
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if re.match(r"ppt/(slides|slideLayouts|slideMasters|notesSlides|notesMasters)/[^/]+\.xml$", item.filename):
                xml = data.decode("utf-8")
                ids = re.findall(r'<p:cNvPr id="(\d+)"', xml)
                if len(ids) != len(set(ids)):
                    n = [1]
                    def sub(m):
                        n[0] += 1
                        return '<p:cNvPr id="%d"' % n[0]
                    xml = re.sub(r'<p:cNvPr id="\d+"', sub, xml)
                    fixed += 1
                    data = xml.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp, path)
    print("renumbered ids in %d parts → %s" % (fixed, path))

if __name__ == "__main__":
    for p in sys.argv[1:]:
        fix(p)
