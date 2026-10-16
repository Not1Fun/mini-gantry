"""逐页渲染并核对文字边界，输出本地审版缩略图。"""
from pathlib import Path
import json
import fitz
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parent


def main():
    qa=ROOT.parents[2]/'qa_v3';qa.mkdir(exist_ok=True);records=[]
    for name in ('manufacturing','assembly_and_procurement'):
        path=ROOT/'drawings'/(name+'.pdf');doc=fitz.open(path);pages=[];errors=[]
        folder=qa/name;folder.mkdir(exist_ok=True)
        for i,page in enumerate(doc):
            text=page.get_text()
            if not text.strip():errors.append(dict(page=i+1,reason='no extractable text'))
            for b in page.get_text('blocks'):
                if b[0]<18 or b[1]<8 or b[2]>page.rect.width-18 or b[3]>page.rect.height-8:errors.append(dict(page=i+1,bbox=list(b[:4]),text=b[4][:100]))
            page.get_pixmap(matrix=fitz.Matrix(.8,.8),alpha=False).save(folder/f'page-{i+1:03d}.png')
            pages.append(folder/f'page-{i+1:03d}.png')
        sheets=[]
        for start in range(0,len(pages),16):
            canvas=Image.new('RGB',(1280,1040),'#d8dfe3');draw=ImageDraw.Draw(canvas)
            for j,p in enumerate(pages[start:start+16]):
                thumb=Image.open(p);thumb.thumbnail((310,235));x=(j%4)*320+(320-thumb.width)//2;y=(j//4)*260+20
                canvas.paste(thumb,(x,y));draw.text(((j%4)*320+8,(j//4)*260+3),f'{name} | {start+j+1}',fill='black')
            sheet=qa/(name+f'-sheet-{start//16+1:02d}.png');canvas.save(sheet);sheets.append(sheet.name)
        records.append(dict(file=str(path.relative_to(ROOT)),pages=len(doc),text_bounds_errors=errors,contact_sheets=sheets))
    result=dict(status='PASS_PDF_TEXT_BOUNDS' if not any(r['text_bounds_errors'] for r in records) else 'FAIL',documents=records,
                visual_review='requires review of rendered contact sheets and representative full pages')
    (ROOT/'validation/pdf_qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
